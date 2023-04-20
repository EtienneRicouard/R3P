import React from "react";
import { JobModel } from "./JobModel";

interface Props {
  pollingInterval: number;
  statusUrl: string;
  job: JobModel;
  onJobCompletion: (job: JobModel) => void;
}

interface State {
  progress: number;
  error?: string;
}

export class ProgressBarPolling extends React.Component<Props, State> {
  state: State = { progress: 0 };
  private timer?: ReturnType<typeof setInterval>;

  componentDidMount() {
    this.timer = setInterval(() => this.getStatus(), this.props.pollingInterval);
  }

  componentDidUpdate(prevProps: Props) {
    // Retrigger the polling mecanism if the jobid has changed
    if(this.props.job.jobId !== prevProps.job.jobId)
    {
      clearInterval(this.timer);
      this.timer = setInterval(() => this.getStatus(), this.props.pollingInterval);
    }
  }

  componentWillUnmount() {
    clearInterval(this.timer);
    this.timer = undefined;
  }

  private async getStatus() {
    if (this.props.job.jobId === '') {
      return;
    }

    try {
      // TODO Add JobId to request
      const response = await fetch(this.props.statusUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
      const status = await response.json();
      const progress = status.iteration / ((status.width * status.height) - 1) * 100;
      this.setState({ progress });
      // No need to keep polling
      // TODO: set back 100 when generation will work
      if (progress > 80) {
        const newJobStatus = { ...this.props.job };
        newJobStatus.completed = true;
        this.props.onJobCompletion(newJobStatus);
        clearInterval(this.timer);
        this.timer = undefined;
      }
    }
    catch(_) {
      this.setState({ error: `Unable to retrieve progress for jobId ${this.props.job.jobId}`, progress: 0});
    }
  }

  render() {
    const progress = `${this.state.progress.toFixed(1)}%`;
    const style = {
      width: progress,
    };
    return (
      <div className="w-64 flex flex-col items-center justify-between">
        <div className="text-sm font-bold text-gray-700 pb-2">Progress Bar with polling:</div>
        <div className="w-full bg-gray-200 rounded-full">
          {this.state.progress !== undefined && <div className="bg-blue-500 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full" style={style}> {progress}</div>}
        </div>
        {this.state.error !== undefined && <div className="error-message">{this.state.error}</div>}
      </div>
    );
  }
}