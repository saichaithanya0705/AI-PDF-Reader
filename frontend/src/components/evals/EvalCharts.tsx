import { useEffect, useRef, useState } from 'react';
import { VARIANT_COLORS, VARIANT_LABELS } from '../../lib/evalTheme';

const GRID = 'rgba(25, 24, 22, 0.09)';
const AXIS_TEXT = '#76716a';
const LABEL_TEXT = '#191816';
const VALUE_TEXT = '#57534e';

const useWidth = <T extends HTMLElement>() => {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
};

type Tooltip = { x: number; y: number; title: string; lines: string[] } | null;

const TooltipBox = ({ tooltip }: { tooltip: Tooltip }) =>
  tooltip ? (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 min-w-[10rem] rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-ink-primary px-phi-3 py-phi-2 text-phi-xs text-paper-50 shadow-float"
      style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, calc(-100% - 10px))' }}
    >
      <div className="font-medium">{tooltip.title}</div>
      {tooltip.lines.map((line) => (
        <div key={line} className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-paper-300">
          {line}
        </div>
      ))}
    </div>
  ) : null;

export const Legend = ({ series }: { series: string[] }) => (
  <div className="flex flex-wrap gap-x-phi-5 gap-y-phi-2 text-phi-xs text-ink-secondary">
    {series.map((name) => (
      <span key={name} className="inline-flex items-center gap-phi-2">
        <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: VARIANT_COLORS[name] }} />
        {VARIANT_LABELS[name] ?? name}
      </span>
    ))}
  </div>
);

interface GroupedBarsProps {
  metrics: { key: string; label: string }[];
  series: string[];
  values: Record<string, Record<string, number>>;
}

/** Horizontal grouped bars on a single 0-1 axis; golden-ratio proportions. */
export const GroupedMetricBars = ({ metrics, series, values }: GroupedBarsProps) => {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tooltip, setTooltip] = useState<Tooltip>(null);
  const labelWidth = 132;
  const right = 48;
  const barHeight = 10;
  const barGap = 4;
  const bandPadding = 16;
  const bandHeight = series.length * (barHeight + barGap) - barGap + bandPadding;
  const top = 10;
  const plotWidth = width - labelWidth - right;
  const height = top + metrics.length * bandHeight + 28;
  const x = (value: number) => labelWidth + Math.max(0, Math.min(1, value)) * plotWidth;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div ref={ref} className="relative w-full" onMouseLeave={() => setTooltip(null)}>
      <svg width={width} height={height} role="img" aria-label="Retrieval metric comparison by variant">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={top} y2={height - 24} stroke={GRID} />
            <text
              x={x(tick)}
              y={height - 8}
              fill={AXIS_TEXT}
              fontSize={11.2}
              fontFamily="IBM Plex Mono, monospace"
              textAnchor="middle"
            >
              {tick.toFixed(2)}
            </text>
          </g>
        ))}
        {metrics.map((metric, metricIndex) => {
          const bandTop = top + metricIndex * bandHeight + bandPadding / 2;
          const best = Math.max(...series.map((name) => values[name]?.[metric.key] ?? 0));
          const labelledSeries = series.find((name) => (values[name]?.[metric.key] ?? 0) === best);
          return (
            <g key={metric.key}>
              <text
                x={labelWidth - 12}
                y={bandTop + (bandHeight - bandPadding) / 2 + 4}
                fill={LABEL_TEXT}
                fontSize={12.6}
                textAnchor="end"
              >
                {metric.label}
              </text>
              {series.map((name, seriesIndex) => {
                const value = values[name]?.[metric.key] ?? 0;
                const y = bandTop + seriesIndex * (barHeight + barGap);
                const barWidth = Math.max(0, x(value) - labelWidth);
                const radius = Math.min(3.8, barWidth / 2);
                const isBest = value === best;
                const showLabel = name === labelledSeries;
                return (
                  <g key={name}>
                    <path
                      d={`M${labelWidth},${y} h${Math.max(0, barWidth - radius)} a${radius},${radius} 0 0 1 ${radius},${radius} v${barHeight - 2 * radius} a${radius},${radius} 0 0 1 ${-radius},${radius} h${-Math.max(0, barWidth - radius)} z`}
                      fill={VARIANT_COLORS[name]}
                    />
                    {showLabel && (
                      <text
                        x={x(value) + 6}
                        y={y + barHeight - 1}
                        fill={VALUE_TEXT}
                        fontSize={11.2}
                        fontFamily="IBM Plex Mono, monospace"
                      >
                        {value.toFixed(2)}
                      </text>
                    )}
                    <rect
                      x={labelWidth}
                      y={y - barGap / 2}
                      width={plotWidth + right}
                      height={barHeight + barGap}
                      fill="transparent"
                      onMouseMove={() =>
                        setTooltip({
                          x: x(value),
                          y,
                          title: `${metric.label} · ${VARIANT_LABELS[name]}`,
                          lines: [`${value.toFixed(3)}${isBest ? ' (best)' : ''}`],
                        })
                      }
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <TooltipBox tooltip={tooltip} />
    </div>
  );
};

interface LatencyBarsProps {
  series: string[];
  latency: Record<string, { p50: number; p95: number }>;
}

/** p50 as the bar, p95 as a whisker on one millisecond axis; golden-ratio row cadence. */
export const LatencyBars = ({ series, latency }: LatencyBarsProps) => {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tooltip, setTooltip] = useState<Tooltip>(null);
  const labelWidth = 176;
  const right = 74;
  const row = 33;
  const top = 6;
  const height = top + series.length * row + 26;
  const plotWidth = width - labelWidth - right;
  const maxValue = Math.max(1, ...series.map((name) => latency[name]?.p95 ?? 0));
  const step = maxValue > 400 ? 200 : maxValue > 100 ? 50 : 10;
  const axisMax = Math.ceil(maxValue / step) * step;
  const x = (value: number) => labelWidth + (value / axisMax) * plotWidth;
  const ticks = Array.from({ length: Math.floor(axisMax / step) + 1 }, (_, i) => i * step);

  return (
    <div ref={ref} className="relative w-full" onMouseLeave={() => setTooltip(null)}>
      <svg width={width} height={height} role="img" aria-label="Retrieval latency by variant">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={top} y2={height - 24} stroke={GRID} />
            <text
              x={x(tick)}
              y={height - 8}
              fill={AXIS_TEXT}
              fontSize={11.2}
              fontFamily="IBM Plex Mono, monospace"
              textAnchor="middle"
            >
              {tick} ms
            </text>
          </g>
        ))}
        {series.map((name, index) => {
          const { p50 = 0, p95 = 0 } = latency[name] ?? {};
          const y = top + index * row + 10;
          const barWidth = Math.max(0, x(p50) - labelWidth);
          const radius = Math.min(3.8, barWidth / 2);
          return (
            <g key={name}>
              <text x={labelWidth - 12} y={y + 9} fill={LABEL_TEXT} fontSize={12.6} textAnchor="end">
                {VARIANT_LABELS[name]}
              </text>
              <path
                d={`M${labelWidth},${y} h${Math.max(0, barWidth - radius)} a${radius},${radius} 0 0 1 ${radius},${radius} v${12 - 2 * radius} a${radius},${radius} 0 0 1 ${-radius},${radius} h${-Math.max(0, barWidth - radius)} z`}
                fill={VARIANT_COLORS[name]}
              />
              <line x1={x(p50)} x2={x(p95)} y1={y + 6} y2={y + 6} stroke="#57534e" strokeWidth={1.5} />
              <line x1={x(p95)} x2={x(p95)} y1={y + 1} y2={y + 11} stroke="#57534e" strokeWidth={1.5} />
              <text
                x={x(p95) + 6}
                y={y + 10}
                fill={VALUE_TEXT}
                fontSize={11.2}
                fontFamily="IBM Plex Mono, monospace"
              >
                p95 {Math.round(p95)}
              </text>
              <rect
                x={labelWidth}
                y={y - 6}
                width={plotWidth + right}
                height={row - 4}
                fill="transparent"
                onMouseMove={() =>
                  setTooltip({
                    x: x(p95),
                    y,
                    title: VARIANT_LABELS[name],
                    lines: [`p50 ${p50.toFixed(1)} ms`, `p95 ${p95.toFixed(1)} ms`],
                  })
                }
              />
            </g>
          );
        })}
      </svg>
      <TooltipBox tooltip={tooltip} />
    </div>
  );
};
