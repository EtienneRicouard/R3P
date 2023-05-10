import { MultiLevelViewport } from './MultiLevelViewport';
import { MultiLevelViewport2 } from './MultiLevelViewport2';

export default function Home() {
  return (
    <main className="p-8">
        {/* {<MultiLevelViewport width={1000} height={600} tileWidth={100} tileHeight={60} zoomSensitivity={100}/>} */}
        {<MultiLevelViewport2 width={256} height={256} tileWidth={256} tileHeight={256}/>}
    </main>
  )
}
