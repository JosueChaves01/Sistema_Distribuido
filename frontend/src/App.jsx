import { useEffect, useState } from "react";
import NodeCard from "./components/NodeCard";

function App() {
  const [nodes, setNodes] = useState({});
  const [file, setFile] = useState(null);

  const fetchNodes = async () => {
    const res = await fetch("http://192.168.0.112:8000/workers");
    const data = await res.json();
    setNodes(data);
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert("Selecciona una imagen");
  
    const formData = new FormData();
    formData.append("file", file);
  
    const res = await fetch("http://192.168.0.112:8000/upload", {
      method: "POST",
      body: formData,
    });
  
    const data = await res.json();
    console.log(data);
  
    if (data.status === "sent") {
      alert("Tarea enviada.");
    } else {
      alert("Error al enviar tarea: " + (data.message || "sin detalle"));
    }
  };

  useEffect(() => {
    fetchNodes();
    const interval = setInterval(fetchNodes, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1>Sistema Distribuido - Nodos Activos</h1>
      {Object.entries(nodes).map(([name, info]) => (
        <NodeCard key={name} name={name} info={info} />
      ))}
      <hr />
      <h2>Subir imagen para procesar</h2>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload}>Enviar imagen</button>
    </div>
  );
}

export default App;