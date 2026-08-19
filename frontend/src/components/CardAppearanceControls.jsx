import { BoxSelect, Layers3, Sparkles } from 'lucide-react';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Switch } from './ui/switch';
import { FRAME_STYLES, TITLE_EFFECTS } from '../lib/cardTypes';

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

export function CardAppearanceControls({
  frame,
  appearance,
  onFrameChange,
  onAppearanceChange,
}) {
  const setAppearance = (patch) => onAppearanceChange({ ...appearance, ...patch });
  const opacity = Math.round((appearance.description_opacity ?? 0.64) * 100);

  return (
    <section className="glass-panel p-6" data-testid="appearance-controls">
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-xl bg-amber-500/10 p-2 text-amber-300">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Aspetto del fronte</h2>
          <p className="mt-1 text-sm text-slate-400">
            Personalizza cornice, titolo e leggibilità della descrizione.
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
          <div className="grid grid-cols-3 gap-2">
            {TITLE_EFFECTS.map((option) => (
              <ChoiceButton
                key={option.id}
                active={appearance.title_effect === option.id}
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
            checked={appearance.title_shadow !== false}
            onCheckedChange={(checked) => setAppearance({ title_shadow: checked })}
          />
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <Label htmlFor="description-opacity" className="text-slate-200">
                Opacità pannello descrizione
              </Label>
              <p className="mt-1 text-xs text-slate-500">Più opaco per artwork molto dettagliati.</p>
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
      </div>
    </section>
  );
}