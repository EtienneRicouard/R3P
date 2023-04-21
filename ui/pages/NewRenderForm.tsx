import React from "react";
import { JobModel } from "./JobModel";

interface Props {
  onSubmit: (job: JobModel) => void;
  renderImageUrl: string;
}

interface State {
  width?: number;
  height?: number;
  error?: string;
  processing: boolean;
}

export class NewRenderForm extends React.Component<Props, State> {
  state: State = { width: 200, height: 100, processing: false };

  private async handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // Sanities: This shouldn't be possible as submit button is disabled
    if (this.state.width === undefined || this.state.height === undefined) {
      const newState = {...this.state};
      newState.error = 'Invalid width/height';
      newState.processing = false;
      this.setState(newState);
      return;
    }
    try {
      // Set the processing state to true to avoid running queries at the same time
      const processingState = {...this.state};
      processingState.processing = true;
      this.setState(processingState);
      // Start a new rendering with the given parameters
      const response = await fetch(this.props.renderImageUrl, {
        method: 'POST',
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          width: this.state.width,
          height: this.state.height,
        }),
      });
      // Retrieve the jobId and update the current job status
      const body = await response.json();

      this.props.onSubmit({jobId: body.message.jobId, completed: false, width: this.state.width, height: this.state.height});
      // Set the state to successful and cleanup the error message
      const newState = {...this.state};
      newState.error = undefined;
      newState.processing = false;
      this.setState(newState);
    }
    catch(_) {
      // Set the current job id to none
      this.props.onSubmit({jobId: "", completed: false, width: 0, height: 0});
      // Create a new error state
      const newState = {...this.state};
      newState.error = 'Failed to contact backend';
      newState.processing = false;
      this.setState(newState);
    }
  }

  private setValue(fieldName: string, newValue: string) {
    const newState = {...this.state};
    const parsedValue = parseInt(newValue, 10);
    // Input validation
    if (isNaN(parsedValue) || parsedValue <= 0) {
      newState[fieldName] = undefined;
      newState.error = "Invalid number";
    }
    else {
      // Update the width/height field with the new value
      newState[fieldName] = parsedValue;
      newState.error = undefined;
    }
    this.setState(newState);
  }

  render() {
    const disabled = this.state.height === undefined || this.state.width === undefined || this.state.processing;
    return (
      <form onSubmit={(e) => this.handleSubmit(e)} className="new-render-form">
        <div className="form-label-container">
          <label className="form-label" htmlFor="width">Width</label>
          <input className="form-input"
            type="number"
            id="width"
            name="width"
            min="1"
            value={this.state.width || ''}
            onChange={e => this.setValue('width', e.target.value)}/>
        </div>
        <div className="form-label-container">
          <label className="form-label" htmlFor="height">Height</label>
          <input className="form-input"
            type="number"
            id="height"
            name="height"
            min="1"
            value={this.state.height || ''}
            onChange={e => this.setValue('height', e.target.value)}/>
        </div>
        <div className="new-render-container">
          <button className={disabled ? "form-button-disabled": "form-button"} disabled={disabled}>
              {this.state.processing ? "Processing..." : "Start"}
          </button>
          {this.state.error !== undefined && <div className="error-message">{this.state.error}</div>}
        </div>
      </form>
    );
  }
 }