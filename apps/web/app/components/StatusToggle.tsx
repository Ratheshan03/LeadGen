import { useState, useEffect } from "react";

type Props = {
  label: string;
  field: string;
  value: boolean;
  id: string;
  onChange: () => void;
};

const StatusToggle = ({ label, field, value, id, onChange }: Props) => {
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    setLoading(true);
    try {
      await updateLeadStatus(id, { [field]: !value });
      onChange();
    } catch (e) {
      alert("Update failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={`px-3 py-1 rounded-full text-white text-xs ${
        value ? "bg-green-600" : "bg-gray-500"
      } hover:opacity-90 transition`}
    >
      {loading ? "..." : `${label}: ${value ? "✅" : "❌"}`}
    </button>
  );
};

export default StatusToggle;
