#define pr_fmt(fmt) "pMonitor: " fmt

#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/fdtable.h>
#include <linux/fs_struct.h>
#include <linux/net.h>
#include <linux/file.h>
#include <linux/timer.h>
#include <linux/module.h>
#include <linux/printk.h>
#include <linux/errno.h>
#include <linux/list.h>
#include <linux/slab.h>
#include <linux/workqueue.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/string.h>
#include <linux/uaccess.h>
#include <linux/sched.h>
#include <net/inet_connection_sock.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("nour");
MODULE_DESCRIPTION("Monitor the TCP queues every 1 second");

/**
 * pmon_entry structure holds the data in a linked list
 *
 * @ts  The timestamp for the entry
 * @listen_q_size   The recorded size of the listen queue
 * @accept_q_size   The recorded size of the accept queue
 *
 * @llist   The kernel list head
 */
struct pmon_entry {
	unsigned int ts;
	unsigned int listen_q_size;
	unsigned int accept_q_size;

	struct list_head llist;
};

#define LOG_INTERVAL 1000 /* default is 1000 msec */

/* the timer that we will use throughout the lifetime of the module */
static struct timer_list pmon_timer;

/* the cache to hold the data until a flush */
static struct kmem_cache *pmon_cache;

static struct workqueue_struct *pmon_wq;
static struct work_struct pmon_work;

static LIST_HEAD(head);

static DEFINE_SPINLOCK(pmon_lock);

static struct proc_dir_entry *proc_entry;

static int sock_fd;
static int pid;
static struct socket *sock;
static struct task_struct *task;
static struct fdtable *files_table;
static struct files_struct *files;

static void pmon_timer_callback(unsigned long data)
{
	/*
	 * This one just schedules the work and sets up the next timer interval
	 */
	int ret;

	ret = queue_work(pmon_wq, &pmon_work);

	if (ret == 0)
		pr_err("Queueing the work in the work queue failed.\n\
		       Will try again in the next interval\n");

	ret = mod_timer(&pmon_timer,
			jiffies + msecs_to_jiffies(LOG_INTERVAL));
}

static void pmon_work_callback(struct work_struct *work)
{
	struct pmon_entry *entry;

	BUG_ON(sock == NULL);

	entry = (struct pmon_entry *) kmem_cache_alloc(pmon_cache, GFP_KERNEL);
	if (IS_ERR(entry)) {
		pr_err ("failed to allocate cache space for a new entry\n");
		return;
	}

	entry->ts = jiffies_to_msecs(jiffies);
	entry->listen_q_size = inet_csk_reqsk_queue_len(sock->sk);
	entry->accept_q_size = sock->sk->sk_ack_backlog;

	spin_lock_bh(&pmon_lock);
	list_add_tail(&(entry->llist), &head);
	spin_unlock_bh(&pmon_lock);
	pr_info("work completed...\n");
}

static void *pmon_start(struct seq_file *s, loff_t *pos)
{
	/* should acquire locks here to avoid bad things from happening */
	spin_lock_bh(&pmon_lock);
	return seq_list_start(&head, *pos);
}

static void *pmon_next(struct seq_file *s, void *v, loff_t *pos)
{
	return seq_list_next(v, &head, pos);
}

static void pmon_stop(struct seq_file *s, void *v)
{
	/* should release locks when we get here! */
	spin_unlock_bh(&pmon_lock);
}

static int pmon_show(struct seq_file *s, void *v)
{
	struct pmon_entry *entry = list_entry((struct list_head *)v,
			   struct pmon_entry, llist);

	seq_printf(s, "%u;%u;%u\n",
		   entry->ts,
		   entry->listen_q_size,
		   entry->accept_q_size);
	return 0;
}

static const struct seq_operations pmon_seq_ops = {
	.start = pmon_start,
	.next  = pmon_next,
	.stop  = pmon_stop,
	.show  = pmon_show,
};

static int pmon_open(struct inode *inode, struct file *file)
{
	return seq_open(file, &pmon_seq_ops);
}

static ssize_t pmon_write(struct file *s, const char __user *buffer,
		      unsigned long count, loff_t *data)
{
	char *buff;
	int ret,i;

	buff = (char *)kmalloc(count+1, GFP_KERNEL);
	if (IS_ERR(buff)) {
		pr_err("out of memory, could not create buffer space\n");
		return -ENOMEM;
	}

	if (copy_from_user(buff, buffer, count)) {
		pr_err("could not copy message from user space\n");
		ret = -EFAULT;
		goto exit_on_error;
	}
	if (buff[count-1] == '\n') {/*remove trailing endline from echo*/
		buff[count-1] = '\0';
	}
	buff[count] = '\0';

	if (strcmp(buff, "1") == 0) {
		/* enable the module, first check if it is already
		 * active before reactivation */
		if (timer_pending(&pmon_timer) == 1) {
			pr_info("module already active");
		} else if (sock == NULL) {
			pr_err("cannot activate module, no socket defined");
		} else {
			ret = mod_timer(&pmon_timer,
					jiffies
					+ msecs_to_jiffies(LOG_INTERVAL));
			pr_info("module activated");
		}
	} else if (strcmp(buff, "0") == 0) {
		/* disable the module */
		flush_workqueue(pmon_wq);
		del_timer(&pmon_timer);
		pr_info("module deactivated");
	} else if (buff[0] == 'F') {
		/* get the socket file descriptor */
		if (sock_fd != 0)
			goto exit;

		ret = kstrtoint(&(buff[2]), 10, &sock_fd);
		if (ret != 0) {
			pr_err("invalid socket descriptor input");
			if (ret == -ERANGE)
				pr_err("range error");
			else
				pr_err("format error");
			sock_fd = 0;
			goto exit_on_error;
		}

		pr_info("got the socket fd=%d", sock_fd);
		sock = sockfd_lookup(sock_fd, &ret);
		if (!sock) {
			pr_err("could not find socket, message is %d",
			       ret);
			sock_fd = 0;
			goto exit_on_error;
		}
		pr_info("found the socket with fd=%d", sock_fd);
	} else if (buff[0] == 'P') {
		/* lookup task by its pid provided */
		if (pid != -1)
			goto exit;

		ret = kstrtoint(&(buff[2]), 10, &pid);
		if (ret != 0) {
			pid = -1;
			goto exit_on_error;
		}

		pr_info("got process id to look for pid=%d", pid);
		task = pid_task(find_vpid(pid), PIDTYPE_PID);
		if (!task) {
			pr_err("could not find the task with pid=%d", pid);
			pid = -1;
			goto exit_on_error;
		}

		pr_info("found task struct with pid=%d", pid);

		/*files = get_files_struct(task);*/
		files = task->files;
		if (!files) {
			pr_err("could not get files struct");
			pid = -1;
			task = NULL;
			goto exit_on_error;
		}

		pr_info("starting iteration through fdtable");
		files_table = files_fdtable(files);
		if (!files_table) {
			pr_err("could not get the filetable");
			goto exit_on_error;
		}
		while(i < files_table->max_fds &&
		      files_tables->fd[i]) {
			pr_info("in interation with index %d", i);
			sock = sock_from_file(files_table->fd[i], &ret);
			if (sock) {
				pr_info("found socket in files of the process");
			}
			i++;
		}
	} else {
		pr_err("unrecognized command!");
		ret = -EFAULT;
		goto exit_on_error;
	}

exit:
	kfree(buff);
	return count;

exit_on_error:
	kfree(buff);
	return ret;
}

static const struct file_operations pmon_file_ops = {
	.owner	 = THIS_MODULE,
	.open	 = pmon_open,
	.read	 = seq_read,
	.write   = pmon_write,
	.llseek  = seq_lseek,
	.release = seq_release,
};

static int __init pmon_init(void)
{
	int ret=0;

	pr_info("module loading...\n");

	/* setup the timer_list with the callback function */
	setup_timer(&pmon_timer, pmon_timer_callback, 0);

	/* now try to allocate the memory space needed using slab allocator
	*/
	pmon_cache = kmem_cache_create("pmon_cache", sizeof(struct pmon_entry),
				       0, 0, NULL);
	if (!pmon_cache) {
		pr_err("failed to create slab cache\n");
		ret = -ENOMEM;
		goto exit_on_timer;
	}

	pmon_wq = create_workqueue("pmon_wq");
	if (!pmon_wq) {
		pr_err("failed to create work queue\n");
		ret = -ENOMEM;
		goto exit_on_cache;
	}

	/* initialize the work to be used for logging but will not start logging
	 * until first timer has fired
	 */
	INIT_WORK(&pmon_work, pmon_work_callback);

	proc_entry = proc_create("pmonitor", 0, NULL, &pmon_file_ops);
	if (!proc_entry) {
		pr_err("failed to create procfs entry...\n");
		ret = -ENOMEM;
		goto exit_on_workq;
	}

	sock_fd = 0;
	sock = NULL;
	pid = -1;
	task = NULL;

	pr_info("module_loaded...\n");
	return 0;

exit_on_workq:
	flush_workqueue(pmon_wq);
	destroy_workqueue(pmon_wq);
exit_on_cache:
	kmem_cache_destroy(pmon_cache);
exit_on_timer:
	del_timer(&pmon_timer);

	return ret;
}

static void __exit pmon_cleanup(void)
{
	struct pmon_entry *next, *temp;

	/* for us there's no need to check if the timer was active or
	 * inactive, it doesn't really matter as we are exiting anyway
	 */
	del_timer(&pmon_timer);


	flush_workqueue(pmon_wq);
	destroy_workqueue(pmon_wq);

	/* must remove everything from the list and free up the memory
	 */
	list_for_each_entry_safe(next, temp, &head, llist) {
		list_del(&(next->llist));
		kmem_cache_free(pmon_cache, next);
	}

	kmem_cache_destroy(pmon_cache);
	remove_proc_entry("pmonitor", NULL);

	/* fix reference counts for the file, better not to create a mess here
	 */
	if (sock)
		sockfd_put(sock);

	pr_info("module unloaded...\n");
}

module_init(pmon_init);
module_exit(pmon_cleanup);
