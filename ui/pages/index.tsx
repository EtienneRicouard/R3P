import { MultiLevelViewport } from './MultiLevelViewport';

export default function Home() {
  return (
    <main className="p-8">
        {<MultiLevelViewport width={1000} height={600} tileWidth={100} tileHeight={60} zoomSensitivity={10}/>}

    </main>
  )
}
