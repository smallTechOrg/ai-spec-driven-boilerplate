import { useState, useEffect } from 'react';
import { UploadScreen } from './components/UploadScreen';
import { ChatScreen } from './components/ChatScreen';
import { StubBanner } from './components/StubBanner';
import { getHealth, type SessionInfo } from './api';

export default function App() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [llmProvider, setLlmProvider] = useState('stub');

  useEffect(() => {
    getHealth().then(h => setLlmProvider(h.llm_provider)).catch(() => {});
  }, []);

  return (
    <>
      <StubBanner provider={llmProvider} />
      {session
        ? <ChatScreen session={session} onReset={() => setSession(null)} />
        : <UploadScreen onSessionReady={setSession} />
      }
    </>
  );
}
