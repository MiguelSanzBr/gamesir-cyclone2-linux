import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './adapters/ui/App'
import { DemoTransport } from './adapters/demo/demo'
import { WebHidTransport, hidSupported } from './adapters/webhid/webhid'

// raiz de composição: liga os adapters de saída (WebHID, demo) na UI
createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App ports={{ hidSupported: hidSupported(), pick: () => WebHidTransport.connect(), demo: () => new DemoTransport() }} />
  </StrictMode>,
)
