export default function SampleDataCard({ title, description, icon }) {
  return (
    <div className="insight-card">
      <div className="card-header">
        <span className="card-icon">{icon}</span>
        <h4>{title}</h4>
      </div>
      <p>{description}</p>
    </div>
  );
}
