import React from "react";
import { JobModel } from "./JobModel";

interface Props {
  uiUrl: string;
  job: JobModel;
}

interface State {
  error?: string;
  colorUnique?: boolean;
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

  private verifyColor(): void {
    if (this.canvas === null) {
      return;
    }
    const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D;
    const imageData = ctx.getImageData(0, 0, this.props.job.width, this.props.job.height);
    const colorSet = new Set();
    for (let i = 0; i < imageData.data.length; i += 4) {
      const r = imageData.data[i];
      const g = imageData.data[i + 1];
      const b = imageData.data[i + 2];
      const a = imageData.data[i + 3];
      colorSet.add((r << 24) + (g << 16) + (b << 8) + (a));
    }

    this.setState({ colorUnique: colorSet.size === this.props.job.width * this.props.job.height });
  }

  render() {
    return (
      <>
        <canvas ref={node => (this.canvas = node)} width={this.props.job.width} height={this.props.job.height}/>
        {this.state.error === undefined && <button onClick={() => this.verifyColor()} className="form-button">Verify color uniqueness:</button>}
        {this.state.error === undefined && this.state.colorUnique !== undefined
          && <div className="regular-text">{this.state.colorUnique ? "All colors are unique" : "At least one color is duplicated"}</div>}
        {this.state.error !== undefined
          && <div className="error-message">{this.state.error}</div>}
      </>
    );
  }
}