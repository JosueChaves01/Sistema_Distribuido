
const formatBytes = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(2) + " " + sizes[i];
};

const NodeCard = ({ name, info }) => {
  return (
    <div className="card">
      <h3>{name}</h3>
      <p><strong>CPU:</strong> {info.cpu}%</p>
      <p><strong>RAM:</strong> {info.ram}%</p>
      <p><strong>Red:</strong> {formatBytes(info.net)}</p>
      <p><em>IP:</em> {info.ip}</p>
    </div>
  );
};

export default NodeCard;
