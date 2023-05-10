import React from "react";

interface Props {
  width: number;
  height: number;
  tileWidth: number;
  tileHeight: number;
  zoomSensitivity: number;
}

interface State {
  s: number;
  center: [number, number];
  tiles: number[];
}

export class MultiLevelViewport extends React.Component<Props, State> {
  canvas: HTMLCanvasElement | null = null;
  private drag = false;
  private startDragPosition: [number, number] = [0, 0];
  private startDragCenter: [number, number] = [0, 0];

  constructor(props: Props) {
    super(props);
    const tiles = [];
    const length = props.width / props.tileWidth * props.height / props.tileHeight;
    for (let i = 0; i <= length; i++) {
      tiles.push(i);
    }
    this.state = {
      s: 1,
      center: [props.width / 2, props.height / 2],
      tiles,
    };
  }

  componentDidUpdate(_: Props) {
    this.drawCanvas();
  }

  componentDidMount() {
    this.drawCanvas();
    if (this.canvas === null) {
      return;
    }
    this.handlePanMove.bind(this);
    this.canvas.addEventListener('mousedown', this.handlePanStart);
    this.canvas.addEventListener('mousemove', this.handlePanMove);
    this.canvas.addEventListener('mouseup', this.handlePanEnd);
    this.canvas.addEventListener('wheel', this.handleMouseWheel)
  }

  private drawCanvas() {
    if (this.canvas === null) {
      return;
    }
    const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D;
    ctx.clearRect(0, 0, this.props.width, this.props.height);

    this.state.tiles.forEach(tile => {
      // Retrieve x/y position for tile
      const x = tile%(this.props.width / this.props.tileWidth) * this.props.tileWidth;
      const y = Math.floor(tile / (this.props.width / this.props.tileWidth)) * this.props.tileHeight;
      ctx.fillStyle = "#00FF00";
      ctx.fillRect(x, y, this.props.tileWidth, this.props.tileHeight);
      ctx.fillStyle = "#000000";
      ctx.strokeStyle = "1px solid #000000";
      ctx.strokeRect(x, y, this.props.tileWidth, this.props.tileHeight);
      // Hack to center text in tile
      ctx.fillText(`${tile}`, x + this.props.tileWidth / 2 - 5, y + this.props.tileHeight / 2);
    });

    ctx.strokeStyle = "2px solid #FF0000";
    ctx.strokeRect(this.state.center[0] - (this.props.width * this.state.s / 2),
      this.state.center[1] - (this.props.height * this.state.s / 2),
      this.props.width*this.state.s,
      this.props.height*this.state.s);

    // Debug
    // Draw center
    ctx.beginPath();
    ctx.strokeStyle = "#000000";
    ctx.arc(this.state.center[0], this.state.center[1], 3, 0, 2 * Math.PI, true);
    ctx.stroke();
  }

  private handlePanStart = (event: MouseEvent): void => {
    this.startDragPosition = [event.x, event.y];
    this.startDragCenter = [this.state.center[0], this.state.center[1]];
    this.drag = true;
  }

  private handlePanMove = (event: MouseEvent): void => {
    if (this.drag) {
      const translated = [event.x - this.startDragPosition[0], event.y - this.startDragPosition[1]];
      const newCenter: [number, number] = [this.startDragCenter[0] + translated[0], this.startDragCenter[1] + translated[1]];
      const tiles = this.computeTileIntersection(newCenter, this.state.s);
      const state = { ...this.state, center: newCenter, tiles };
      this.setState(state);
    }
  }

  private handlePanEnd = (_: MouseEvent): void => {
    this.drag = false;
  }

  private handleMouseWheel = (event: WheelEvent): void => {
    const delta = Math.sign(event.deltaY);
    const newS = this.state.s + (delta / this.props.zoomSensitivity);
    if (newS < 0 || newS > 1) {
      return;
    }
    const tiles = this.computeTileIntersection(this.state.center, newS);
    const state = { ...this.state, tiles, s: newS };
    this.setState(state);
  }

  private computeTileIntersection(center: [number, number], s: number): number[] {
    const intersections: number[] = [];
    const topLeftCorner = [center[0] - this.props.width / 2 * s, center[1] - this.props.height / 2 * s];
    const length = this.props.width / this.props.tileWidth * this.props.height / this.props.tileHeight;
    // Loop on all tiles and verify if it is in the drawn rectangle
    for (let tileIndex = 0; tileIndex <= length; tileIndex++) {
      const x = tileIndex%(this.props.width / this.props.tileWidth) * this.props.tileWidth;
      const y = Math.floor(tileIndex / (this.props.width / this.props.tileWidth)) * this.props.tileHeight;
      // Check left border
      if (x + this.props.tileWidth < topLeftCorner[0]) {
        continue;
      }
      // Check right border
      if (x > topLeftCorner[0] + this.props.width * s) {
        continue;
      }
      // Check top border
      if (y + this.props.tileHeight < topLeftCorner[1]) {
        continue;
      }
      // Check bottom border
      if (y > topLeftCorner[1] + this.props.height * s) {
        continue;
      }
      intersections.push(tileIndex);
    }
    return intersections;
  }

  render() {
    return (
      <div className="row-start-1 row-span-3 col-start-2 col-span-2">
        <div className="flex flex-col items-center">
          <canvas ref={node => (this.canvas = node)}
          className="mb-8"
          width={this.props.width}
          height={this.props.height}
          style={{
            cursor: "pointer",
            border: "2px dashed #FF0000",
            width: `${this.props.width}px`,
            height: `${this.props.height}px`
          }}
          />
        </div>
      </div>
    );
  }
}