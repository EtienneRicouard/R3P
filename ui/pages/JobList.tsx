import React from 'react';
import { JobStatus } from './JobStatus';

const jobProgress = (job: JobStatus): string => {
  const progress = job.iteration / (job.height * job.width) * 100;
  return `${progress.toFixed(1)}%`;
}

interface Props {
  jobList: JobStatus[];
  currentJob: string;
  onJobSelect: (job: string) => void;
}
export class JobList extends React.Component<Props> {

  render() {
    return (
      this.props.jobList.length !== 0 && (<ul role="list" className="divide-y divide-gray-100 bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
        {this.props.jobList.map((job) => (
          <li onClick={() => this.props.onJobSelect(job.jobId)} key={job.jobId} className="flex justify-between gap-x-6 py-5 hover:bg-gray-200 hover:cursor-pointer">
            <div className="flex gap-x-4">
              <div className="min-w-0 flex-auto">
                <p className="text-sm font-semibold leading-6 text-gray-900">{job.jobId}</p>
                <p className="mt-1 truncate text-xs leading-5 text-gray-500">{job.created}</p>
              </div>
            </div>
            <div className="hidden sm:flex sm:flex-col sm:items-end">
              <p className="text-sm leading-6 text-gray-900">{job.width} x {job.height}</p>
            </div>
            <div className="w-64 flex flex-col items-center justify-between">
              <div className="w-full bg-gray-200 rounded-full">
                <div className="bg-blue-500 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full" style={{ width: jobProgress(job) }}> {jobProgress(job)}</div>
              </div>
            </div>
          </li>
        ))}
      </ul>)
    )
  }
}
