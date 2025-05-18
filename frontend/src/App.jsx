import { useEffect, useState } from "react";
import NodeCard from "./components/NodeCard";
import "./App.css";

function App() {
  //const [nodes, setNodes] = useState({});
  const [queueSize, setQueueSize] = useState(0);
  const [file, setFile] = useState(null);
  const [tps, setTps] = useState(0);
  const [nodes, setNodes] = useState({
    "worker-1": {
      cpu: 45,
      ram: 70,
      net: 123456,
      ip: "192.168.0.101",
      status: "libre",
      task_id: null,
      isCoordinator: true,
    },
    "worker-2": {
      cpu: 30,
      ram: 50,
      net: 789012,
      ip: "192.168.0.102",
      status: "ejecutando tarea",
      task_id: "abc123",
      isCoordinator: false,
    },
  });

  const fetchStatus = async () => {
    try {
      const [nodesRes, queueRes, tpsRes] = await Promise.all([
        fetch("http://100.120.4.105:8000/workers"),
        fetch("http://100.120.4.105:8000/queue_size"),
        fetch("http://100.120.4.105:8000/tps"),
      ]);

      const nodesData = await nodesRes.json();
      const queueData = await queueRes.json();
      const tpsData = await tpsRes.json();

      setNodes(nodesData);
      setQueueSize(queueData.pending_tasks);
      setTps(tpsData.tps);
    } catch (err) {
      console.error("Error al obtener estado:", err);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert("Selecciona una imagen");

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://100.120.4.105:8000/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (data.status === "sent") {
      alert("Tarea enviada.");
    } else {
      alert("Error al enviar tarea: " + (data.message || "sin detalle"));
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 900);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container">
      <h1>Sistema Distribuido</h1>
      <h3>Tareas en cola: {queueSize}</h3>
      <h3>Tareas procesadas por segundo (TPS): {tps}</h3>

      <div className="card-list">
        {Object.entries(nodes).map(([name, info]) => (
          <NodeCard
            key={name}
            name={name}
            info={info}
            isCoordinator={info.isCoordinator}
          />
        ))}
      </div>

      <hr />

      <h2>Subir imagen para procesar</h2>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload}>Enviar imagen</button>
    </div>
  );
}

export default App;
