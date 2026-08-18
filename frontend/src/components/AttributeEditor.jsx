import React from "react";
import { Plus, Trash2 } from "lucide-react";
import { attrLabel } from "@/lib/cardTypes";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const inputCls = "bg-input border-border rounded-none font-body focus-visible:ring-gold text-sm";

const ObjectListEditor = ({ value, onChange }) => {
  const items = Array.isArray(value) ? value : [];
  const keys = items.length ? Object.keys(items[0]) : ["nome", "descrizione"];
  const update = (idx, k, v) => {
    const next = items.map((it, i) => (i === idx ? { ...it, [k]: v } : it));
    onChange(next);
  };
  const add = () => onChange([...items, keys.reduce((a, k) => ({ ...a, [k]: "" }), {})]);
  const remove = (idx) => onChange(items.filter((_, i) => i !== idx));
  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={idx} className="border border-border bg-obsidian/40 p-3 relative">
          <button type="button" onClick={() => remove(idx)}
            className="absolute top-2 right-2 text-muted-foreground hover:text-crimson transition-colors">
            <Trash2 className="w-4 h-4" />
          </button>
          {keys.map((k) => (
            <div key={k} className="mb-2 last:mb-0 pr-6">
              <Label className="font-label text-[10px] tracking-wide text-gold/70 uppercase">{attrLabel(k)}</Label>
              {k === "descrizione" || String(it[k]).length > 40 ? (
                <Textarea value={it[k] ?? ""} onChange={(e) => update(idx, k, e.target.value)} className={`${inputCls} mt-1 min-h-[60px]`} />
              ) : (
                <Input value={it[k] ?? ""} onChange={(e) => update(idx, k, e.target.value)} className={`${inputCls} mt-1`} />
              )}
            </div>
          ))}
        </div>
      ))}
      <Button type="button" variant="outline" onClick={add}
        className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[11px] tracking-wide h-8">
        <Plus className="w-3.5 h-3.5 mr-1" /> Aggiungi
      </Button>
    </div>
  );
};

const StringListEditor = ({ value, onChange }) => {
  const text = Array.isArray(value) ? value.join("\n") : (value || "");
  return (
    <Textarea
      value={text}
      onChange={(e) => onChange(e.target.value.split("\n"))}
      placeholder="Un elemento per riga"
      className={`${inputCls} min-h-[80px]`}
    />
  );
};

export default function AttributeEditor({ attributes, onChange, allowCustomFields }) {
  const attrs = attributes || {};

  const setField = (key, val) => onChange({ ...attrs, [key]: val });
  const removeField = (key) => {
    const next = { ...attrs };
    delete next[key];
    onChange(next);
  };
  const addField = () => {
    let i = 1;
    let key = `campo_${i}`;
    while (attrs[key] !== undefined) { i += 1; key = `campo_${i}`; }
    onChange({ ...attrs, [key]: "" });
  };

  return (
    <div className="space-y-5">
      {Object.entries(attrs).map(([key, val]) => {
        const isObjList = Array.isArray(val) && val.length > 0 && typeof val[0] === "object";
        const isStrList = Array.isArray(val) && !isObjList;
        const isLong = typeof val === "string" && val.length > 60;
        return (
          <div key={key}>
            <div className="flex items-center justify-between mb-1.5">
              <Label className="font-label text-xs tracking-widest text-gold/80 uppercase">{attrLabel(key)}</Label>
              {allowCustomFields && (
                <button type="button" onClick={() => removeField(key)} className="text-muted-foreground hover:text-crimson transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            {isObjList ? (
              <ObjectListEditor value={val} onChange={(v) => setField(key, v)} />
            ) : isStrList ? (
              <StringListEditor value={val} onChange={(v) => setField(key, v)} />
            ) : isLong ? (
              <Textarea data-testid={`attr-${key}`} value={val} onChange={(e) => setField(key, e.target.value)} className={`${inputCls} min-h-[70px]`} />
            ) : (
              <Input data-testid={`attr-${key}`} value={val ?? ""} onChange={(e) => setField(key, e.target.value)} className={inputCls} />
            )}
          </div>
        );
      })}
      {allowCustomFields && (
        <Button type="button" variant="outline" onClick={addField}
          className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[11px] tracking-wide h-8">
          <Plus className="w-3.5 h-3.5 mr-1" /> Aggiungi campo
        </Button>
      )}
    </div>
  );
}
