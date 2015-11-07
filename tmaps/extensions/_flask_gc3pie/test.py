from engine import BgEngine
import logging
import gc3libs
import time
import re



logger = logging.getLogger(__name__)

task = gc3libs.Application(
    arguments='hostname',
    jobname='test_hostname',
    output_dir='/Users/Robin/gc3libs_test',
    stdout='test_hostname.out',
    inputs=[],
    outputs=[]
)


def submit_jobs(self, jobs, monitoring_interval=5, monitoring_depth=2):
    logger.debug('monitoring interval: %ds' % monitoring_interval)

    # Create an `Engine` instance for running jobs in parallel
    e = gc3libs.create_engine()
    # Put all output files in the same directory
    e.retrieve_overwrites = True

    # change 'gevent' to 'threading' if running with Flask's debug
    # webserver instead of uWSGI
    bg = BgEngine('gevent', e)

    # Add tasks to engine instance
    bg.add(jobs)

    # start the background thread; instruct it to run `e.progress()`
    # every `monitoring_interval` seconds
    bg.start(monitoring_interval)

    # periodically check the status of submitted jobs and output a
    # report in JSON format
    with open('/Users/robin/Desktop/status.txt', 'a') as f:

        # I guess the body of this `while` loop should be changed into
        # an AJAX method that outputs the current state in JSON format
        # and exits, but I'm keeping the old structure as I'm not
        # familiar with the big picture of TissueMAPS --RM
        while True:

            status = {
              'name': jobs.jobname,
              'time': self.create_datetimestamp(),
            }

            # this creates a *dictionary* mapping task IDs to data;
            # the old code from submit_job() uses an array instead
            # so I'm going to convert
            task_data_by_id = bg.task_and_children_data()
            status['jobs'] = [task_data for task_data in task_data_by_id.values() if task_data['name'] != jobs.jobname]
            # Now, the following would get you some data about the
            # number of currently SUBMITTED, RUNNING, TERMINATED,
            # etc. jobs:
            #
            #     aggregate = bg.stats_data()
            #
            # However, the original code excludes some jobs from the
            # count (those which end in `_<number>`) so I'm going to keep it

            # NOTE: status of jobs could be "SUBMITTED" instead of "RUNNING"
            # in case jobs terminated very quickly
            currently_processed_job = list(set([
                j['name'] for j in status['jobs']
                if j['state'] in {
                    gc3libs.Run.State.RUNNING,
                    gc3libs.Run.State.SUBMITTED,
                    gc3libs.Run.State.TERMINATING,
                    gc3libs.Run.State.TERMINATED
                }
                and not re.search(r'_\d+$', j['name'])
            ]))
            if len(currently_processed_job) > 0:
                terminated_count = 0
                total_count = 0
                for j in status['jobs']:
                    if j['name'].startswith(currently_processed_job[-1]):
                        total_count += 1
                        if j['state'] == gc3libs.Run.State.TERMINATED:
                            terminated_count += 1
                if total_count > 0:
                    terminated_percent = int(float(terminated_count) / float(total_count) * 100)
                else:
                    terminated_percent = 0
            else:
                terminated_count = 0
                total_count = 0
                terminated_percent = 0
            status['terminated'] = terminated_percent
            f.write(self.status_file, status)

            # break out of the loop when all jobs are done
            aggregate = bg.stats_data()
            if aggregate['count_terminated'] == aggregate['count_total']:
                break

            time.sleep(monitoring_interval)

        # A SequentialTaskCollection has exit code == 0 iff the last
        # task had exit code == 0
        status['success'] = (jobs.execution.exitcode == 0)
        f.write(self.status_file, status)

    return True
