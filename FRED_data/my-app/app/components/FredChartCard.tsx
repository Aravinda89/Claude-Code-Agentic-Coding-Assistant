"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SeriesData, SeriesSpec } from "../lib/fred";

const LINE = "#3171de";
const AXIS_TEXT = "#333333";
const GRID = "#d4d4d4";
const FRAME = "#c6c6c6";

// Insets of the plotting rectangle inside the responsive container. They mirror
// the chart margins plus the axis sizes below, so the white FRED plot frame can
// be positioned behind the SVG.
const PLOT = { left: 30, right: 10, top: 6, bottom: 20 };
const CHART_HEIGHT = 220;

function FredWordmark() {
  return (
    <div className="flex shrink-0 items-end gap-1">
      <span className="text-[15px] font-black leading-none tracking-[-0.04em] text-black">
        FRED
      </span>
      <span className="text-[6px] leading-[1.9] text-black">®</span>
      <svg
        viewBox="0 0 24 16"
        aria-hidden
        className="h-4 w-6 rounded-[2px] border border-[#c6d3e6] bg-white"
      >
        <polyline
          points="3,12 7,7 10,10 14,4 17,8 21,3"
          fill="none"
          stroke={LINE}
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
}

type FredTooltipProps = {
  active?: boolean;
  payload?: ReadonlyArray<{ value?: unknown }>;
  label?: React.ReactNode;
  format: (value: number) => string;
};

function FredTooltip({ active, payload, label, format }: FredTooltipProps) {
  const value = payload?.[0]?.value;
  if (!active || typeof value !== "number") return null;
  return (
    <div className="rounded-[3px] border border-[#c6c6c6] bg-white px-2 py-1 text-[10px] text-black shadow-sm">
      <span className="font-bold">{label}:</span> <span>{format(value)}</span>
    </div>
  );
}

export default function FredChartCard({
  spec,
  data,
}: {
  spec: SeriesSpec;
  /** `null` when the series could not be loaded from FRED. */
  data: SeriesData | null;
}) {
  const format = (value: number) => value.toFixed(data?.decimals ?? 0);

  return (
    <section className="flex flex-col">
      <h2 className="mb-2 text-[15px] font-bold leading-tight text-black">
        {spec.title}
      </h2>

      <div className="rounded-md border border-[#d5e0ee] bg-[#ecf3fa] px-3 pt-2 pb-2">
        {/* Header: FRED wordmark and the series legend. */}
        <div className="mb-1 flex items-center gap-3">
          <FredWordmark />
          <div className="flex min-w-0 items-center gap-2">
            <span
              className="h-[2px] w-5 shrink-0 rounded-full"
              style={{ backgroundColor: LINE }}
            />
            <span className="truncate text-[9px] font-bold text-black">
              {spec.legend}
            </span>
          </div>
        </div>

        {/* Plot: a white framed rectangle sits behind the Recharts SVG so the
            axis labels stay on the card background, the way FRED renders it. */}
        <div className="flex">
          <div className="flex w-4 shrink-0 items-center justify-center">
            <span className="whitespace-nowrap text-[9px] text-[#333] [writing-mode:vertical-rl] rotate-180">
              {spec.yLabel}
            </span>
          </div>

          <div className="relative min-w-0 flex-1">
            <div
              className="pointer-events-none absolute border bg-white"
              style={{
                left: PLOT.left,
                right: PLOT.right,
                top: PLOT.top,
                bottom: PLOT.bottom,
                borderColor: FRAME,
              }}
            />
            {data ? (
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart
                  data={data.points}
                  margin={{ top: PLOT.top, right: PLOT.right, bottom: 0, left: 0 }}
                >
                  <CartesianGrid
                    vertical={false}
                    stroke={GRID}
                    strokeWidth={1}
                    syncWithTicks
                  />
                  {data.recession && (
                    <ReferenceArea
                      x1={data.recession.from}
                      x2={data.recession.to}
                      fill="#cdcfd0"
                      fillOpacity={1}
                      ifOverflow="hidden"
                    />
                  )}
                  <XAxis
                    dataKey="label"
                    ticks={data.xTicks}
                    height={PLOT.bottom}
                    tickLine={false}
                    axisLine={{ stroke: FRAME }}
                    tick={{ fontSize: 9, fill: AXIS_TEXT }}
                    tickMargin={5}
                    minTickGap={12}
                  />
                  <YAxis
                    width={PLOT.left}
                    domain={data.domain}
                    ticks={data.yTicks}
                    tickFormatter={format}
                    tickLine={false}
                    axisLine={{ stroke: FRAME }}
                    tick={{ fontSize: 9, fill: AXIS_TEXT }}
                    tickMargin={4}
                  />
                  {data.zeroLine && (
                    <ReferenceLine y={0} stroke="#202020" strokeWidth={1.5} />
                  )}
                  <Tooltip
                    cursor={{ stroke: "#9aa5b5", strokeDasharray: "3 3" }}
                    content={(props) => (
                      <FredTooltip {...props} format={format} />
                    )}
                  />
                  <Line
                    type="linear"
                    dataKey="value"
                    stroke={LINE}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3, fill: LINE, strokeWidth: 0 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div
                className="flex items-center justify-center text-[11px] text-[#6b7280]"
                style={{ height: CHART_HEIGHT }}
              >
                Could not load {spec.id} from FRED.
              </div>
            )}
          </div>
        </div>

        {/* Footer: FRED source attribution. */}
        <div className="mt-1 space-y-0.5 text-[9px] text-[#333]">
          <p>
            Source: Organization for Economic Co-operation and Development via
            FRED®
          </p>
          <div className="flex items-end justify-between gap-2">
            <p className="italic text-[#3171de]">
              Shaded areas indicate U.S. recessions.
            </p>
            <div className="flex shrink-0 items-center gap-2">
              <span>fred.stlouisfed.org</span>
              <span className="flex items-center gap-1 rounded-[3px] border border-[#3171de] px-1.5 py-0.5 text-[#3171de]">
                Fullscreen
                <svg viewBox="0 0 10 10" aria-hidden className="h-2 w-2">
                  <path
                    d="M0.5 3.5v-3h3M9.5 3.5v-3h-3M0.5 6.5v3h3M9.5 6.5v3h-3"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  />
                </svg>
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
