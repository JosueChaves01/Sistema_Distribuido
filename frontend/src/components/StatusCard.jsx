const StatusCard = ({ queueSize, tps }) => (
  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
    <div className="status-card card">
      <div style={{ textAlign: 'center' }}>
        <strong>Tareas en cola:</strong>
        <div style={{ color: '#194dcf', fontWeight: 600, fontSize: 22 }}>{queueSize}</div>
      </div>
    </div>
    <div className="status-card card">
      <div style={{ textAlign: 'center' }}>
        <strong>Tareas por Segundo:</strong>
        <div style={{ color: '#194dcf', fontWeight: 600, fontSize: 22 }}>{tps}</div>
      </div>
    </div>
  </div>
);

export default StatusCard;
