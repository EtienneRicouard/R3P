import React from "react";
import { NebulaRepository } from "./NebulaRepository";

interface Props {
}

interface State {
  resLevel: number;
  centerWorld: [number, number];
  tiles: number[];
}

const TILE_WIDTH = 256;
const TILE_HEIGHT = 256;

export class MultiLevelViewport2 extends React.Component<Props, State> {
  canvas: HTMLCanvasElement | null = null;
  private drag = false;
  private startDragPosition: [number, number] = [0, 0];
  private startDragCenter: [number, number] = [0, 0];
  private cache = new NebulaRepository();

  constructor(props: Props) {
    super(props);
    this.state = {
      resLevel: 1,
      centerWorld: [TILE_WIDTH / 2, TILE_HEIGHT / 2],
      tiles: [0],
    };
  }

  private getWidth(resLevel: number): number {
    return this.getSubdivisions(resLevel)*256;
  }

  private getHeight(resLevel: number): number {
    return this.getSubdivisions(resLevel)*256;
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

  private getScaleFactor(resLevel: number): number {
    return 1 / Math.pow(2, resLevel - 1);
  }

  private getSubdivisions(resLevel: number): number {
    return Math.pow(2, resLevel - 1);
  }

  private async queryTiles(tiles: number[], resLevel: number): Promise<void> {
    try {
      tiles.forEach(async tile => {
        const blob = await this.cache.get(resLevel, tile);
        if (blob === undefined) {
          return;
        }
        const ctx = this.canvas!.getContext("2d") as CanvasRenderingContext2D;
        const tileWidth = this.getWidth(this.state.resLevel) / this.getSubdivisions(this.state.resLevel);
        const tileHeight = this.getHeight(this.state.resLevel) / this.getSubdivisions(this.state.resLevel);
        const x = tile%(this.getWidth(this.state.resLevel) / tileWidth) * tileWidth;
        const y = Math.floor(tile / (this.getWidth(this.state.resLevel) / tileWidth)) * tileHeight;
        const img = new Image();
        img.onload = () => {
          ctx.drawImage(img, x, y);
        };
        img.src = URL.createObjectURL(blob);
      })
    }
    catch(_) {
    }
  }

  private drawCanvas() {
    if (this.canvas === null) {
      return;
    }
    const s = this.getScaleFactor(this.state.resLevel);
    const ctx = this.canvas.getContext("2d") as CanvasRenderingContext2D;
    const width = this.getWidth(this.state.resLevel);
    const height = this.getHeight(this.state.resLevel);
    ctx.clearRect(0, 0, width, height);
    // this.state.tiles.forEach(tile => {
    //   // Retrieve x/y position for tile
    //   const tileWidth = width / this.getSubdivisions(this.state.resLevel);
    //   const tileHeight = height / this.getSubdivisions(this.state.resLevel);
    //   const x = tile%(width / tileWidth) * tileWidth;
    //   const y = Math.floor(tile / (width / tileWidth)) * tileHeight;
    //   ctx.fillStyle = "#00FF00";
    //   ctx.fillRect(x, y, tileWidth, tileHeight);
    //   ctx.fillStyle = "#000000";
    //   ctx.strokeStyle = "1px solid #000000";
    //   ctx.strokeRect(x, y, tileWidth, tileHeight);
    //   ctx.fillText(`${tile}`, x + tileWidth / 2, y + tileHeight / 2);
    // });

    ctx.strokeStyle = "2px solid #FF0000";
    ctx.strokeRect(this.state.centerWorld[0] - (width * s / 2),
      this.state.centerWorld[1] - (height * s / 2),
      width * s,
      height * s);

    // Debug
    // Draw center
    ctx.beginPath();
    ctx.strokeStyle = "#000000";
    ctx.arc(this.state.centerWorld[0], this.state.centerWorld[1], 3, 0, 2 * Math.PI, true);
    ctx.stroke();
    this.queryTiles(this.state.tiles, this.state.resLevel);
  }

  private handlePanStart = (event: MouseEvent): void => {
    this.startDragPosition = [event.x, event.y];
    this.startDragCenter = [this.state.centerWorld[0], this.state.centerWorld[1]];
    this.drag = true;
  }

  private handlePanMove = (event: MouseEvent): void => {
    if (this.drag) {
      const translated = [event.x - this.startDragPosition[0], event.y - this.startDragPosition[1]];
      const newCenter: [number, number] = [this.startDragCenter[0] + translated[0],
                                            this.startDragCenter[1] + translated[1]];
      const tiles = this.computeTileIntersection(newCenter, this.state.resLevel);
      const state = { ...this.state, centerWorld: newCenter, tiles };
      this.setState(state);
    }
  }

  private handlePanEnd = (_: MouseEvent): void => {
    this.drag = false;
  }

  private handleMouseWheel = (event: WheelEvent): void => {
    const direction = Math.sign(event.deltaY);
    const newResLevel = this.state.resLevel + direction;
    if (newResLevel < 1 || newResLevel > 6) {
      return;
    }
    const tiles = this.computeTileIntersection(this.state.centerWorld, newResLevel);
    const state = { ...this.state, tiles, resLevel: newResLevel };
    this.setState(state);
    this.drawCanvas();
  }

  private computeTileIntersection(center: [number, number], resLevel: number): number[] {
    const intersections: number[] = [];
    const s = this.getScaleFactor(resLevel);
    const width = this.getWidth(resLevel);
    const height = this.getHeight(resLevel);
    const topLeftCorner = [center[0] - width / 2 * s, center[1] - height / 2 * s];
    const tileWidth = width / this.getSubdivisions(resLevel);
    const tileHeight = height / this.getSubdivisions(resLevel);
    const length = width / tileWidth * height / tileHeight;
    // Loop on all tiles and verify if it is in the drawn rectangle
    for (let tileIndex = 0; tileIndex <= length; tileIndex++) {
      const x = tileIndex%(width / tileWidth) * tileWidth;
      const y = Math.floor(tileIndex / (width / tileWidth)) * tileHeight;
      // Check left border
      if (x + tileWidth < topLeftCorner[0]) {
        continue;
      }
      // Check right border
      if (x > topLeftCorner[0] + width * s) {
        continue;
      }
      // Check top border
      if (y + tileHeight < topLeftCorner[1]) {
        continue;
      }
      // Check bottom border
      if (y > topLeftCorner[1] + height * s) {
        continue;
      }
      intersections.push(tileIndex);
    }
    return intersections;
  }

  render() {
    const width = this.getWidth(this.state.resLevel);
    const height = this.getHeight(this.state.resLevel);
    return (
      <div className="row-start-1 row-span-3 col-start-2 col-span-2">
        <div className="flex flex-col items-center">
          <canvas ref={node => (this.canvas = node)}
          className="mb-8"
          width={width}
          height={height}
          style={{
            cursor: "pointer",
            border: "2px dashed #FF0000",
            width: `${width}px`,
            height: `${height}px`
          }}
          />
        </div>
      </div>
    );
  }
}