import { useState } from 'react';
import { NewRenderForm } from './NewRenderForm';
import { ProgressBarPolling } from './ProgressBarPolling';
import { PingPongCanvas } from './PingPongCanvas';

export default function Home() {
  const [job, setJob] = useState({ jobId: "", completed: false, width: 0, height: 0 });
  const baseBackendURL = "http://localhost:8000/pingpong";

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <NewRenderForm onSubmit={setJob} renderImageUrl={`${baseBackendURL}/create/`} />
      <ProgressBarPolling job={job} onJobCompletion={setJob} pollingInterval={1000} statusUrl={`${baseBackendURL}/status`}/>
      <PingPongCanvas job={job} uiUrl={`${baseBackendURL}/render`}/>
    </main>
  )
}
