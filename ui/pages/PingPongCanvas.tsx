import React from "react";
import { JobModel } from "./JobModel";

interface Props {
  uiUrl: string;
  job: JobModel;
}

interface State {
  error?: string;
}

export class PingPongCanvas extends React.Component<Props, State> {
  state: State = { };
  canvas: HTMLCanvasElement | null = null;

  componentDidUpdate(prevProps: Props) {
    // Retrigger the polling mecanism if the jobid has changed
    if(this.props.job.jobId === prevProps.job.jobId
      && this.props.job.completed !== prevProps.job.completed
      && this.props.job.completed)
    {
      this.getImage();
    }
  }

  private async getImage() {
    if (this.props.job.jobId === '' || this.canvas === null) {
      return;
    }

    this.setState({ error: undefined });

    try {
      const response = await fetch(`${this.props.uiUrl}/${this.props.job.jobId}/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
      const bytes = await response.arrayBuffer();
      const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D ;
      const imageData = new ImageData(new Uint8ClampedArray(bytes), this.props.job.width, this.props.job.height);
      ctx.putImageData(imageData, 0, 0);
    }
    catch(_) {
      this.setState({ error: `Unable to render image for jobId ${this.props.job.jobId}` });
    }
  }

  render() {
    return (
      <>
        <canvas ref={node => (this.canvas = node)} width={this.props.job.width} height={this.props.job.height}/>
        {this.state.error !== undefined && <div className="error-message">{this.state.error}</div>}
      </>
    );
  }
}