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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <h3 style={{ margin: 0 }}>
          <span style={{ color: "#194dcf" }}>{name}</span>
        </h3>
        {isCoordinator && (
          <span
            style={{
              background: "#194dcf",
              color: "white",
              padding: "2px 10px",
              borderRadius: "12px",
              fontSize: "0.85em",
              fontWeight: "bold",
              marginLeft: "10px",
              marginTop: "2px",
              whiteSpace: "nowrap",
            }}
          >
            Coordinador
          </span>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "center", marginTop: "8px" }}>
        <p style={{ margin: 0 }}>
          <strong>CPU:</strong> {info.cpu}%
        </p>
      </div>
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
    </div>
  );
};

export default NodeCard;
