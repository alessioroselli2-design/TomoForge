import { BoxSelect, Layers3, Palette, Sparkles, Type } from 'lucide-react';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Switch } from './ui/switch';
import {
  DEFAULT_APPEARANCE,
  FRAME_STYLES,
  TEXT_COLORS,
  TEXT_PANEL_COLORS,
  TITLE_EFFECTS,
} from '../lib/cardTypes';

function ChoiceButton({ active, label, colors, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-xl border p-2 text-left transition-all ${
        active
          ? 'border-amber-400 bg-amber-500/10 ring-1 ring-amber-400'
          : 'border-slate-700 bg-slate-950/40 hover:border-slate-500'
      }`}
    >
      <span
        className="mb-2 block h-7 rounded-md border border-white/10"
        style={{ background: `linear-gradient(120deg, ${colors.join(', ')})` }}
      />
      <span className="text-xs font-semibold text-slate-100">{label}</span>
    </button>
  );
}

function ColorPalette({ id, label, hint, options, value, onChange, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-3">
      <Label className="mb-1 flex items-center gap-2 text-slate-200">
        <Icon className="h-4 w-4" />
        {label}
      </Label>
      <p className="mb-3 text-xs text-slate-500">{hint}</p>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.color)}
            aria-label={option.label}
            aria-pressed={value.toLowerCase() === option.color.toLowerCase()}
            title={option.label}
            className={`group rounded-lg border p-1.5 transition-all ${
              value.toLowerCase() === option.color.toLowerCase()
                ? 'border-amber-400 ring-1 ring-amber-400'
                : 'border-slate-700 hover:border-slate-500'
            }`}
          >
            <span
              className="block h-7 rounded-md border border-white/15 shadow-inner"
              style={{ backgroundColor: option.color }}
            />
            <span className="mt-1 block truncate text-[9px] text-slate-400 group-hover:text-slate-200">
              {option.label}
            </span>
          </button>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 border-t border-slate-800 pt-3">
        <input
          id={id}
          type="color"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-9 w-11 cursor-pointer border border-slate-600 bg-slate-900 p-1"
        />
        <Label htmlFor={id} className="text-xs text-slate-400">
          Colore personalizzato
        </Label>
        <span className="ml-auto rounded bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-300">
          {value.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

export function CardAppearanceControls({
  frame,
  appearance,
  onFrameChange,
  onAppearanceChange,
}) {
  const setAppearance = (patch) => onAppearanceChange({ ...appearance, ...patch });
  const normalizedAppearance = { ...DEFAULT_APPEARANCE, ...appearance };
  const opacity = Math.round((normalizedAppearance.description_opacity ?? 0.64) * 100);

  return (
    <section className="glass-panel p-6" data-testid="appearance-controls">
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-xl bg-amber-500/10 p-2 text-amber-300">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Aspetto del fronte</h2>
          <p className="mt-1 text-sm text-slate-400">
            Personalizza cornice, titolo, pannello testi e leggibilità di descrizione e storia.
          </p>
        </div>
      </div>

      <div className="space-y-5">
        <div>
          <Label className="mb-2 flex items-center gap-2 text-slate-300">
            <BoxSelect className="h-4 w-4" />
            Cornice foil
          </Label>
          <div className="grid grid-cols-3 gap-2">
            {FRAME_STYLES.map((option) => (
              <ChoiceButton
                key={option.id}
                active={frame === option.id}
                label={option.label}
                colors={
                  option.id === 'gold'
                    ? ['#fff3a3', '#d97706', '#78350f']
                    : option.id === 'silver'
                      ? ['#ffffff', '#94a3b8', '#334155']
                      : ['#fb7185', '#facc15', '#34d399', '#60a5fa', '#c084fc']
                }
                onClick={() => onFrameChange(option.id)}
              />
            ))}
          </div>
        </div>

        <div>
          <Label className="mb-2 flex items-center gap-2 text-slate-300">
            <Layers3 className="h-4 w-4" />
            Finitura del titolo
          </Label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {TITLE_EFFECTS.map((option) => (
              <ChoiceButton
                key={option.id}
                active={normalizedAppearance.title_effect === option.id}
                label={option.label}
                colors={option.colors}
                onClick={() => setAppearance({ title_effect: option.id })}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950/40 p-3">
          <div>
            <Label htmlFor="title-shadow" className="text-slate-200">Ombra 3D del titolo</Label>
            <p className="mt-1 text-xs text-slate-500">Aggiunge profondità senza cambiare la finitura.</p>
          </div>
          <Switch
            id="title-shadow"
            checked={normalizedAppearance.title_shadow !== false}
            onCheckedChange={(checked) => setAppearance({ title_shadow: checked })}
          />
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <Label htmlFor="description-opacity" className="text-slate-200">
                Opacità pannello testi
              </Label>
              <p className="mt-1 text-xs text-slate-500">Più opaco per artwork molto dettagliati o testo chiaro.</p>
            </div>
            <span className="min-w-11 rounded-md bg-slate-800 px-2 py-1 text-center text-xs font-semibold text-amber-200">
              {opacity}%
            </span>
          </div>
          <Slider
            id="description-opacity"
            min={30}
            max={90}
            step={5}
            value={[opacity]}
            onValueChange={([value]) => setAppearance({ description_opacity: value / 100 })}
          />
        </div>

        <ColorPalette
          id="text-panel-color"
          label="Sfondo descrizione e storia"
          hint="Scegli una base scura o chiara per aumentare il contrasto."
          options={TEXT_PANEL_COLORS}
          value={normalizedAppearance.text_panel_color}
          onChange={(text_panel_color) => setAppearance({ text_panel_color })}
          icon={Palette}
        />

        <ColorPalette
          id="text-color"
          label="Colore scrittura"
          hint="Si applica al testo della carta e ai blocchi descrizione/storia."
          options={TEXT_COLORS}
          value={normalizedAppearance.text_color}
          onChange={(text_color) => setAppearance({ text_color })}
          icon={Type}
        />
      </div>
    </section>
  );
}