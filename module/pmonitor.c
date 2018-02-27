#include <linux/kernel.h>
#include <linux/timer.h>
#include <linux/module.h>
#include <linux/printk.h>
#include <linux/errno.h>
#include <linux/list.h>
#include <linux/slab.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("nour");
MODULE_DESCRIPTION("Monitor the TCP queues every 1 second");

/* pmon_entry structure holds the data in a linked list
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

/* the timer that we will use throughout the lifetime of the module */
static struct timer_list pmon_timer;

/* the cache to hold the data until a flush */
static struct kmem_cache *pmon_cache;

LIST_HEAD(head);

static void pmon_timer_callback(unsigned long data)
{
}

static int __init pmon_init(void)
{
	int ret;

	pr_info("pMonitor module installing...\n");

	/* setup the timer_list with the callback function */
	setup_timer(&pmon_timer, pmon_timer_callback, 0);

	ret = mod_timer(&pmon_timer,
			jiffies + msecs_to_jiffies(1000));

	/* we should not here unless the timer has expired and
	 * is no longer active. so ret should be zero
	 */
	if (ret) {
		pr_err("mod_timer returned that the timer is still active!\n");

		del_timer(&pmon_timer);
		return -ETIME; /* returning timer expired here, but means something different */
	}

	/* now try to allocate the memory space needed using slab
	*/
	pmon_cache = kmem_cache_create("pmon_cache", sizeof(struct pmon_entry),
				       0, 0, 0);

	return 0;
}

static void __exit pmon_cleanup(void)
{
	/* for us there's no need to check if the timer was active or
	 * inactive, it doesn't really matter as we are exiting anyway
	 */
	del_timer(&pmon_timer);

	kmem_cache_destroy(pmon_cache);
	pmon_cache = NULL;
}

module_init(pmon_init);
module_exit(pmon_cleanup);
