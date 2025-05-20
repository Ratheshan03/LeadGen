"use client";

import { useState, useEffect } from "react";
import { searchLeads, fetchLeads } from "@/app/lib/api";
import StatusToggle from "@/app/components/StatusToggle";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<LeadType[]>([]);

  const refreshLeads = async () => {
    const data = await fetchLeads();
    setResults(data.leads || []);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await searchLeads(query);
      setResults(data.leads || []);
    } catch (err) {
      alert("Search failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshLeads();
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-100 to-gray-200 p-8">
      <div className="max-w-9xl mx-auto">
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h1 className="text-4xl font-extrabold text-indigo-700 drop-shadow-md">
            LeadGen Dashboard
          </h1>

          <form
            onSubmit={handleSearch}
            className="flex w-full max-w-md gap-2"
            aria-label="Search leads form"
          >
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search businesses..."
              className="flex-grow px-4 py-3 rounded-lg border border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
              aria-label="Search businesses"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </form>
        </header>

        <section>
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">
            Saved Leads
          </h2>

          {results.length > 0 ? (
            <div className="overflow-x-auto rounded-lg shadow-lg bg-white border border-gray-200">
              <table className="min-w-full table-auto border-collapse">
                <thead className="bg-indigo-50 sticky top-0">
                  <tr>
                    <th className="text-left px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Business Name
                    </th>
                    <th className="text-left px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Address
                    </th>
                    <th className="text-left px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Website
                    </th>
                    <th className="text-left px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Phone
                    </th>
                    <th className="text-center px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Contacted
                    </th>
                    <th className="text-center px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Email Sent
                    </th>
                    <th className="text-center px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      SMS Sent
                    </th>
                    <th className="text-center px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Cold Called
                    </th>
                    <th className="text-center px-6 py-3 text-indigo-700 font-semibold uppercase text-sm whitespace-nowrap">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((lead, i) => (
                    <tr
                      key={lead._id || i}
                      className={`border-t ${
                        i % 2 === 0 ? "bg-white" : "bg-indigo-50"
                      } hover:bg-indigo-100 transition`}
                    >
                      <td
                        className="px-6 py-4 max-w-xs truncate"
                        title={lead.name}
                      >
                        <span className="font-semibold text-indigo-800">
                          {lead.name}
                        </span>
                      </td>
                      <td
                        className="px-6 py-4 max-w-xs truncate"
                        title={lead.address}
                      >
                        {lead.address}
                      </td>
                      <td className="px-6 py-4 max-w-xs truncate">
                        {lead.website ? (
                          <a
                            href={lead.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-600 hover:underline"
                            title={lead.website}
                          >
                            {lead.website}
                          </a>
                        ) : (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </td>
                      <td className="px-2 py-4">
                        {lead.phone || (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </td>

                      {/* Status Toggles */}
                      <td className="px-6 py-4 text-center">
                        <StatusToggle
                          label="Contacted"
                          field="contacted"
                          value={lead.contacted}
                          id={lead._id}
                          onChange={refreshLeads}
                        />
                      </td>
                      <td className="px-6 py-4 text-center">
                        <StatusToggle
                          label="Email Sent"
                          field="email_sent"
                          value={lead.email_sent}
                          id={lead._id}
                          onChange={refreshLeads}
                        />
                      </td>
                      <td className="px-6 py-4 text-center">
                        <StatusToggle
                          label="SMS Sent"
                          field="sms_sent"
                          value={lead.sms_sent}
                          id={lead._id}
                          onChange={refreshLeads}
                        />
                      </td>
                      <td className="px-6 py-4 text-center">
                        <StatusToggle
                          label="Cold Called"
                          field="cold_called"
                          value={lead.cold_called}
                          id={lead._id}
                          onChange={refreshLeads}
                        />
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => alert(`Edit ${lead.name}`)}
                          className="px-2 py-1 w-25 m-1 bg-yellow-400 hover:bg-yellow-500 text-white rounded shadow-sm transition"
                          aria-label={`Edit lead ${lead.name}`}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => alert(`Delete ${lead.name}`)}
                          className="px-2 py-1 w-25 m-1 bg-red-500 hover:bg-red-600 text-white rounded shadow-sm transition"
                          aria-label={`Delete lead ${lead.name}`}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-600 italic">No leads saved yet.</p>
          )}
        </section>
      </div>
    </main>
  );
}
