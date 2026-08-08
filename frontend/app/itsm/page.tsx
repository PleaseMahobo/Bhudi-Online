'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/shared/auth/AuthContext';
import ModuleShell from '@/shared/components/ModuleShell';
import { useRouter } from 'next/navigation';
import {
  listTickets,
  createTicket,
  setTicketStatus,
  deleteTicket,
  listAssets,
  linkTicketAsset,
  unlinkTicketAsset,
  listWorkNotes,
  addWorkNote,
  runWarrantyExpiryJob,
  type ServiceTicket,
  type Asset,
  type WorkNote,
} from '@/lib/api';
import {
  Ticket,
  Plus,
  Trash2,
  ArrowLeft,
  Save,
  X,
  RefreshCw,
  Link2,
  MessageSquare,
  AlertTriangle,
} from 'lucide-react';

const STATUSES = ['new', 'open', 'in_progress', 'on_hold', 'resolved', 'closed'];
const TYPES = ['incident', 'service_request', 'problem', 'change'];
const PRIORITIES = ['low', 'medium', 'high', 'critical'];

const emptyTicket = {
  title: '',
  description: '',
  ticket_type: 'incident',
  priority: 'medium',
  requester: '',
  assignee: '',
  asset_id: '',
};

function priorityColor(p: string) {
  switch (p) {
    case 'critical':
      return 'text-red-400';
    case 'high':
      return 'text-orange-400';
    case 'medium':
      return 'text-amber-300';
    default:
      return 'text-zinc-400';
  }
}

function statusColor(s: string) {
  switch (s) {
    case 'new':
      return 'bg-sky-900/60 text-sky-300';
    case 'open':
    case 'in_progress':
      return 'bg-amber-900/60 text-amber-300';
    case 'on_hold':
      return 'bg-zinc-700 text-zinc-300';
    case 'resolved':
    case 'closed':
      return 'bg-emerald-900/60 text-emerald-300';
    default:
      return 'bg-zinc-700 text-zinc-300';
  }
}

export default function ItsmPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tickets, setTickets] = useState<ServiceTicket[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterPriority, setFilterPriority] = useState('');

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyTicket });

  const [selected, setSelected] = useState<ServiceTicket | null>(null);
  const [notes, setNotes] = useState<WorkNote[]>([]);
  const [noteBody, setNoteBody] = useState('');
  const [linkAssetId, setLinkAssetId] = useState('');

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 2500);
  };

  const loadData = useCallback(async () => {
    try {
      setBusy(true);
      setError(null);
      const [t, a] = await Promise.all([
        listTickets({
          status: filterStatus || undefined,
          ticket_type: filterType || undefined,
          priority: filterPriority || undefined,
        }),
        listAssets(),
      ]);
      setTickets(t);
      setAssets(a);
    } catch (e: any) {
      setError(e?.message || 'Failed to load ITSM data');
    } finally {
      setBusy(false);
    }
  }, [filterStatus, filterType, filterPriority]);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  useEffect(() => {
    if (!loading && user) loadData();
  }, [loading, user, loadData]);

  const selectTicket = async (ticket: ServiceTicket) => {
    setSelected(ticket);
    setNoteBody('');
    try {
      const n = await listWorkNotes(ticket.id);
      setNotes(n);
    } catch {
      setNotes([]);
    }
  };

  const saveTicket = async () => {
    try {
      setBusy(true);
      setError(null);
      const payload = {
        title: form.title,
        description: form.description || null,
        ticket_type: form.ticket_type,
        priority: form.priority,
        requester: form.requester || null,
        assignee: form.assignee || null,
        asset_ids: form.asset_id ? [form.asset_id] : undefined,
      };
      const created = await createTicket(payload);
      flash(`Ticket ${created.number} created`);
      setShowForm(false);
      setForm({ ...emptyTicket });
      await loadData();
      await selectTicket(created);
    } catch (e: any) {
      setError(e?.message || 'Failed to create ticket');
    } finally {
      setBusy(false);
    }
  };

  const onStatus = async (ticket: ServiceTicket, status: string) => {
    try {
      setBusy(true);
      const updated = await setTicketStatus(ticket.id, status);
      flash(`Status → ${status}`);
      await loadData();
      await selectTicket(updated);
    } catch (e: any) {
      setError(e?.message || 'Failed to update status');
    } finally {
      setBusy(false);
    }
  };

  const removeTicket = async (id: string) => {
    if (!confirm('Delete this ticket?')) return;
    try {
      await deleteTicket(id);
      flash('Ticket deleted');
      if (selected?.id === id) setSelected(null);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete ticket');
    }
  };

  const onLinkAsset = async () => {
    if (!selected || !linkAssetId) return;
    try {
      await linkTicketAsset(selected.id, linkAssetId, 'related');
      flash('Asset linked');
      setLinkAssetId('');
      await loadData();
      const list = await listTickets({});
      const t = list.find((x) => x.id === selected.id);
      if (t) await selectTicket(t);
    } catch (e: any) {
      setError(e?.message || 'Failed to link asset');
    }
  };

  const onUnlink = async (assetId: string) => {
    if (!selected) return;
    try {
      await unlinkTicketAsset(selected.id, assetId);
      flash('Asset unlinked');
      const list = await listTickets({});
      const t = list.find((x) => x.id === selected.id);
      if (t) await selectTicket(t);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to unlink asset');
    }
  };

  const onAddNote = async () => {
    if (!selected || !noteBody.trim()) return;
    try {
      await addWorkNote(selected.id, noteBody.trim(), user?.email);
      setNoteBody('');
      const n = await listWorkNotes(selected.id);
      setNotes(n);
      flash('Note added');
    } catch (e: any) {
      setError(e?.message || 'Failed to add note');
    }
  };

  const onWarrantyJob = async () => {
    try {
      setBusy(true);
      const created = await runWarrantyExpiryJob(30);
      flash(`Warranty job opened ${created.length} ticket(s)`);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Warranty job failed');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <ModuleShell title="ITSM">
        <div className="text-slate-500">Loading…</div>
      </ModuleShell>
    );
  }

  return (
    <ModuleShell title="ITSM" subtitle="Tickets, work notes & asset linkage">
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onWarrantyJob}
              className="flex items-center gap-2 bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-800 px-4 py-2.5 rounded-lg text-sm"
            >
              <AlertTriangle size={16} /> Warranty scan
            </button>
            <button
              onClick={loadData}
              className="flex items-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-lg text-sm text-slate-700"
            >
              <RefreshCw size={16} /> Refresh
            </button>
            <button
              onClick={() => {
                setForm({ ...emptyTicket });
                setShowForm(true);
              }}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 px-4 py-2.5 rounded-lg font-medium text-white text-sm"
            >
              <Plus size={18} /> New Ticket
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-700 text-sm">
            {success}
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <select
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="">All types</option>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
          >
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            {tickets.length === 0 && !busy && (
              <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-slate-500 shadow-sm">
                No tickets match the current filters.
              </div>
            )}
            {tickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => selectTicket(ticket)}
                className={`bg-white border rounded-xl p-5 cursor-pointer transition shadow-sm ${
                  selected?.id === ticket.id
                    ? 'border-indigo-500 ring-1 ring-indigo-200'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-3 mb-1">
                      <span className="text-indigo-600 font-mono text-sm">{ticket.number}</span>
                      <h3 className="text-base font-semibold text-slate-900">{ticket.title}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(ticket.status)}`}>
                        {ticket.status}
                      </span>
                      <span className={`text-xs font-medium ${priorityColor(ticket.priority)}`}>
                        {ticket.priority}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-slate-500">
                      <span>{ticket.ticket_type}</span>
                      {ticket.assignee && <span>Assignee: {ticket.assignee}</span>}
                      {ticket.asset_links && ticket.asset_links.length > 0 && (
                        <span className="text-indigo-600">
                          {ticket.asset_links.length} asset link(s)
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <select
                      className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800"
                      value={ticket.status}
                      onChange={(e) => onStatus(ticket, e.target.value)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => removeTicket(ticket.id)}
                      className="p-2 rounded-lg bg-slate-50 hover:bg-red-50 text-red-500 border border-slate-200"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="xl:col-span-1">
            <div className="bg-white border border-slate-200 rounded-xl p-5 sticky top-4 space-y-5 shadow-sm">
              {!selected ? (
                <p className="text-slate-500 text-sm text-center py-10">
                  Select a ticket to manage assets and work notes.
                </p>
              ) : (
                <>
                  <div>
                    <div className="text-indigo-600 font-mono text-sm">{selected.number}</div>
                    <h3 className="text-base font-semibold mt-1 text-slate-900">{selected.title}</h3>
                    {selected.description && (
                      <p className="text-xs text-slate-500 mt-2">{selected.description}</p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 font-medium text-sm mb-2 text-slate-800">
                      <Link2 size={14} /> Linked assets
                    </div>
                    <div className="space-y-2 mb-3">
                      {(selected.asset_links || []).length === 0 && (
                        <p className="text-xs text-slate-500">No assets linked</p>
                      )}
                      {(selected.asset_links || []).map((link) => (
                        <div
                          key={link.id}
                          className="flex items-center justify-between text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
                        >
                          <span className="text-slate-700">
                            {link.asset_name || link.asset_tag || link.asset_id.slice(0, 8)}
                            {link.asset_status && (
                              <span className="text-slate-500"> · {link.asset_status}</span>
                            )}
                          </span>
                          <button
                            onClick={() => onUnlink(link.asset_id)}
                            className="text-red-500 hover:text-red-600"
                          >
                            Unlink
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <select
                        className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800"
                        value={linkAssetId}
                        onChange={(e) => setLinkAssetId(e.target.value)}
                      >
                        <option value="">Select asset…</option>
                        {assets.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name} {a.asset_tag ? `(${a.asset_tag})` : ''}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={onLinkAsset}
                        disabled={!linkAssetId}
                        className="px-3 py-2 rounded-lg bg-indigo-600 text-xs font-medium text-white disabled:opacity-40"
                      >
                        Link
                      </button>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 font-medium text-sm mb-2 text-slate-800">
                      <MessageSquare size={14} /> Work notes
                    </div>
                    <div className="space-y-2 max-h-40 overflow-y-auto mb-3">
                      {notes.length === 0 && (
                        <p className="text-xs text-slate-500">No notes yet</p>
                      )}
                      {notes.map((n) => (
                        <div
                          key={n.id}
                          className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
                        >
                          <div className="text-slate-500 mb-0.5">
                            {n.author || 'system'} · {new Date(n.created_at).toLocaleString()}
                          </div>
                          <div className="text-slate-800">{n.body}</div>
                        </div>
                      ))}
                    </div>
                    <textarea
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm min-h-[72px] text-slate-800"
                      placeholder="Add a work note…"
                      value={noteBody}
                      onChange={(e) => setNoteBody(e.target.value)}
                    />
                    <button
                      onClick={onAddNote}
                      disabled={!noteBody.trim()}
                      className="mt-2 w-full px-3 py-2 rounded-lg bg-indigo-600 text-sm font-medium text-white disabled:opacity-40"
                    >
                      Add note
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {showForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white border border-slate-200 rounded-xl w-full max-w-xl max-h-[90vh] overflow-y-auto p-6 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-slate-900">Create Ticket</h2>
                <button onClick={() => setShowForm(false)} className="p-2 hover:bg-slate-100 rounded-lg">
                  <X size={20} className="text-slate-500" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-500">Title *</label>
                  <input
                    className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Description</label>
                  <textarea
                    className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm min-h-[80px] text-slate-900"
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-500">Type</label>
                    <select
                      className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                      value={form.ticket_type}
                      onChange={(e) => setForm({ ...form, ticket_type: e.target.value })}
                    >
                      {TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Priority</label>
                    <select
                      className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                      value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: e.target.value })}
                    >
                      {PRIORITIES.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-500">Requester</label>
                    <input
                      className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                      value={form.requester}
                      onChange={(e) => setForm({ ...form, requester: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Assignee</label>
                    <input
                      className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                      value={form.assignee}
                      onChange={(e) => setForm({ ...form, assignee: e.target.value })}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Link asset (optional)</label>
                  <select
                    className="w-full mt-1 bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-900"
                    value={form.asset_id}
                    onChange={(e) => setForm({ ...form, asset_id: e.target.value })}
                  >
                    <option value="">None</option>
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2.5 rounded-lg bg-slate-100 text-sm text-slate-700"
                >
                  Cancel
                </button>
                <button
                  onClick={saveTicket}
                  disabled={!form.title || busy}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-sm font-medium text-white disabled:opacity-50"
                >
                  <Save size={16} /> Create Ticket
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ModuleShell>
  );
}
