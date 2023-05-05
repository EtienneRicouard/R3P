import React from "react";
import { JobStatus } from "./JobStatus";

interface Props {
  uiUrl: string;
  jobId: string;
  jobList: JobStatus[];
  pollingInterval: number;
}

interface State {
  error?: string;
  colorUnique?: boolean;
}

export class PingPongCanvas extends React.Component<Props, State> {
  state: State = { };
  canvas: HTMLCanvasElement | null = null;
  private timer?: ReturnType<typeof setInterval>;

  componentDidUpdate(prevProps: Props) {
    // Retrigger the render if jobId has changed
    // Start the polling process
    if(this.props.jobId !== prevProps.jobId)
    {
      clearInterval(this.timer);
      this.getImage();
      this.timer = setInterval(() => this.getImage(), this.props.pollingInterval);
      return;
    }

    const currentJob = this.getCurrentJob();
    // Check if render is finished
    if (currentJob !== undefined && currentJob.iteration === currentJob.width * currentJob.height) {
      // Verify in previous props if the render was already complete
      const previousJob = prevProps.jobList.find(job => job.jobId === this.props.jobId)
      if (previousJob === undefined || previousJob.iteration !== previousJob.width * previousJob.height) {
        // Render is newly finished, update the image instantly instead of waiting for the interval to finish
        clearInterval(this.timer);
        this.getImage();
      }
    }

  }

  componentWillUnmount() {
    clearInterval(this.timer);
    this.timer = undefined;
  }

  private async getImage() {
    const currentJob = this.getCurrentJob();
    if (currentJob === undefined || this.canvas === null) {
      return;
    }

    this.setState({});

    try {
      const response = await fetch(`${this.props.uiUrl}/${this.props.jobId}/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
      const bytes = await response.arrayBuffer();
      const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D ;
      const imageData = new ImageData(new Uint8ClampedArray(bytes), currentJob.width, currentJob.height);
      ctx.putImageData(imageData, 0, 0);
    }
    catch(_) {
      const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D ;
      ctx.clearRect(0, 0, currentJob.width, currentJob.height);
      this.setState({ error: `Unable to render image for jobId ${this.props.jobId}` });
    }

    // Clear the interval
    if (currentJob.iteration === currentJob.width * currentJob.height) {
      clearInterval(this.timer);
    }
  }

  private getCurrentJob(): JobStatus | undefined {
    return this.props.jobList.find(job => job.jobId === this.props.jobId)
  }

  private verifyColor(): void {
    const currentJob = this.getCurrentJob();
    if (this.canvas === null || currentJob === undefined) {
      return;
    }

    const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D;
    const imageData = ctx.getImageData(0, 0, currentJob.width, currentJob.height);
    const colorSet = new Set();
    for (let i = 0; i < imageData.data.length; i += 4) {
      const r = imageData.data[i];
      const g = imageData.data[i + 1];
      const b = imageData.data[i + 2];
      const a = imageData.data[i + 3];
      colorSet.add((r << 24) + (g << 16) + (b << 8) + (a));
    }

    this.setState({ colorUnique: colorSet.size === currentJob.width * currentJob.height });
  }

  render() {
    const currentJob = this.getCurrentJob();
    if (currentJob === undefined) {
      return <></>;
    }
    const jobComplete = currentJob.height * currentJob.width === currentJob.iteration;
    return (
      <div className="row-start-1 row-span-3 col-start-2 col-span-2">
        <div className="flex flex-col items-center">
          <canvas ref={node => (this.canvas = node)} className="mb-8" width={currentJob.width} height={currentJob.height}/>
          {this.state.error === undefined && jobComplete && <button onClick={() => this.verifyColor()} className="mb-8 form-button">Verify color uniqueness:</button>}
          {this.state.error === undefined && jobComplete && this.state.colorUnique !== undefined
            && <div className="mb-8 regular-text">{this.state.colorUnique ? "All colors are unique" : "At least one color is duplicated"}</div>}
          {this.state.error !== undefined
            && <div className="mb-8 error-message">{this.state.error}</div>}
        </div>
      </div>
    );
  }
}