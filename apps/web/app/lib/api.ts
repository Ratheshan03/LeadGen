// lib/api.ts
export async function searchLeads(query: string) {
  const response = await fetch(
    `http://localhost:8000/api/search?query=${encodeURIComponent(query)}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to search leads");
  }

  return response.json();
}

export async function fetchLeads() {
  const response = await fetch("http://localhost:8000/api/leads", {
    next: { revalidate: 0 }, // Optional: disable caching for dev
  });
  if (!response.ok) {
    throw new Error("Failed to fetch leads");
  }
  return response.json();
}



export async function updateLeadStatus(id: string, updates: Partial<any>) {
  const response = await fetch(`http://localhost:8000/api/leads/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error("Failed to update lead");
  }
  return response.json();
}
