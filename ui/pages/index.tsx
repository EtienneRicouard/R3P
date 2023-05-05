import { useEffect, useState } from 'react';
import { NewRenderForm } from './NewRenderForm';
import { PingPongCanvas } from './PingPongCanvas';
import { JobStatus } from './JobStatus';
import { JobList } from './JobList';

export default function Home() {
  const [wsJoblist, setWsJoblist] = useState<null | WebSocket>(null);
  const [jobList, setJoblist] = useState<JobStatus[]>([]);
  const [jobId, setJobId] = useState("");
  const baseBackendURL = "http://localhost:8000/pingpong";
  const baseWebsocketURL = 'ws://localhost:8000/ws/pingpong/';

  useEffect(() => {
    const wsClient = new WebSocket(`${baseWebsocketURL}joblist/`);
    wsClient.onopen = () => {
      setWsJoblist(wsClient);
    };
    wsClient.onclose = () => console.log('ws closed');
    return () => {
      wsClient.close();
    };
  }, []);

  useEffect(() => {
    if (wsJoblist) {
      wsJoblist.onmessage = (evt) => {
        const data = JSON.parse(evt.data);
        if(data['type'] === 'joblist_create') {
          const job = JSON.parse(data['message']);
          setJoblist(oldJobList => [job, ...oldJobList])
        }
        else if(data['type'] === 'joblist_update') {
          setJoblist(oldJobList => {
            const jobNotif = JSON.parse(data['message']);
            const jobsCopy = [...oldJobList];
            // Find the item to update
            const updatedJobIndex = jobsCopy.findIndex(job => job.jobId === jobNotif.jobId);
            if (updatedJobIndex !== -1) {
              const newJob = {
                ...jobsCopy[updatedJobIndex],
                iteration: jobNotif.iteration,
              }
              jobsCopy[updatedJobIndex] = newJob;
              return jobsCopy;
            }
            return oldJobList;
          })
        }
      };
    }
  }, [wsJoblist]);

  return (
    <main className="grid grid-cols-3 grid-rows-3 gap-4 p-8 max-h-screen">
        <NewRenderForm onSubmit={setJobId} renderImageUrl={`${baseBackendURL}/create/`} />
        <JobList jobList={jobList} currentJob={jobId} onJobSelect={setJobId}/>
        <PingPongCanvas jobId={jobId} jobList={jobList} uiUrl={`${baseBackendURL}/render`} pollingInterval={5000}/>
    </main>
  )
}
