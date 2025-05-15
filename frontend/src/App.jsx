import { useEffect, useState } from "react";
import NodeCard from "./components/NodeCard";

function App() {
  const [nodes, setNodes] = useState({});
  const [queueSize, setQueueSize] = useState(0);
  const [file, setFile] = useState(null);

  const fetchStatus = async () => {
    try {
      const [nodesRes, queueRes] = await Promise.all([
        fetch("http://100.124.43.17:8000/workers"),
        fetch("http://100.124.43.17:8000/queue_size"),
      ]);

      const nodesData = await nodesRes.json();
      const queueData = await queueRes.json();

      setNodes(nodesData);
      setQueueSize(queueData.pending_tasks);
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

    const res = await fetch("http://100.124.43.17:8000/upload", {
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
    <div style={{ padding: "2rem" }}>
      <h1>Sistema Distribuido</h1>
      <h3>Tareas en cola: {queueSize}</h3>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {Object.entries(nodes).map(([name, info]) => (
          <NodeCard key={name} name={name} info={info} />
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
