#define pr_fmt(fmt) "pMonitor: " fmt

#include <linux/kernel.h>
#include <linux/timer.h>
#include <linux/module.h>
#include <linux/printk.h>
#include <linux/errno.h>
#include <linux/list.h>
#include <linux/slab.h>
#include <linux/workqueue.h>

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

/*
 * To decide when to flush to disk, we will flush on each page. Each entry is
 * formed of 12 bytes for the logging info and 8 bytes so in total it is 20
 * bytes. The page size is 4 KB so each page should hold about 204 entries. 
 * So I will flush every 200 entries to be conservative.
 */
#define FLUSH_THRESH 200
static unsigned int num_entries;

#define LOG_INTERVAL 1000 /* default is 1000 msec */

/* the timer that we will use throughout the lifetime of the module */
static struct timer_list pmon_timer;

/* the cache to hold the data until a flush */
static struct kmem_cache *pmon_cache;

static struct workqueue_struct *pmon_wq;
static struct work_struct *pmon_work;

static LIST_HEAD(head);

static void pmon_timer_callback(unsigned long data)
{
	/*
	 * This one just schedules the work and sets up the next timer interval
	 */
	int ret;

	ret = queue_work(pmon_wq, pmon_work);

	if (ret == 0)
		pr_err("Queueing the work in the work queue failed.\n\
		       Will try again in the next interval\n");

	ret = mod_timer(&pmon_timer,
			jiffies + msecs_to_jiffies(LOG_INTERVAL));
}

static void pmon_work_callback(struct work_struct *work)
{
	struct pmon_entry *entry;

	entry = (struct pmon_entry *) kmem_cache_alloc(pmon_cache, GFP_KERNEL);
	if (IS_ERR(entry)) {
		pr_err ("failed to allocate cache space for a new entry\n");
		return;
	}

	entry->ts = jiffies_to_msecs(jiffies);
	entry->listen_q_size = 0;
	entry->accept_q_size = 0;

	list_add_tail(&(entry->llist), &head);
}

static int __init pmon_init(void)
{
	int ret=0;

	pr_info("module loading...\n");

	/* setup the timer_list with the callback function */
	setup_timer(&pmon_timer, pmon_timer_callback, 0);

	ret = mod_timer(&pmon_timer,
			jiffies + msecs_to_jiffies(LOG_INTERVAL));

	/* we should not here unless the timer has expired and
	 * is no longer active. so ret should be zero
	 */
	if (ret) {
		pr_err("mod_timer returned that the timer is still active!\n");
		ret = -ETIME; /* returning timer expired here, but means something different */
		goto exit_on_timer;
	}

	/* now try to allocate the memory space needed using slab allocator
	*/
	pmon_cache = kmem_cache_create("pmon_cache", sizeof(struct pmon_entry),
				       0, SLAB_POISON, NULL);
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
	INIT_WORK(pmon_work, pmon_work_callback);

	num_entries = 0;

	return 0;

exit_on_cache:
	kmem_cache_destroy(pmon_cache);
exit_on_timer:
	del_timer(&pmon_timer);

	return ret;
}

static void __exit pmon_cleanup(void)
{
	/* for us there's no need to check if the timer was active or
	 * inactive, it doesn't really matter as we are exiting anyway
	 */
	del_timer(&pmon_timer);

	kmem_cache_destroy(pmon_cache);

	flush_workqueue(pmon_wq);
	destroy_workqueue(pmon_wq);
}

module_init(pmon_init);
module_exit(pmon_cleanup);
