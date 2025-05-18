const formatBytes = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(2) + " " + sizes[i];
};

const NodeCard = ({ name, info, isCoordinator }) => {
  return (
    <div className="card">
      <h3>{name}</h3>
      <p>
        <strong>CPU:</strong> {info.cpu}%
      </p>
      <p>
        <strong>RAM:</strong> {info.ram}%
      </p>
      <p>
        <strong>Red:</strong> {formatBytes(info.net)}
      </p>
      <p>
        <strong>IP:</strong> {info.ip}
      </p>
      <p>
        <strong>Estado:</strong> {info.status || "desconocido"}
      </p>
      <p>
        <strong>Tarea actual:</strong> {info.task_id || "ninguna"}
      </p>
      {isCoordinator && (
        <span
          style={{
            background: "#1976d2",
            color: "#fff",
            padding: "2px 10px",
            borderRadius: "12px",
            fontSize: "0.85em",
            fontWeight: "bold",
            display: "inline-block",
            margin: "0px auto 0 auto",
          }}
        >
          Coordinador
        </span>
      )}
    </div>
  );
};

export default NodeCard;
