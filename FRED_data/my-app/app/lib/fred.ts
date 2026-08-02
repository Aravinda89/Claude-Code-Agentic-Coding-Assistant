/**
 * Loads the dashboard's economic series straight from FRED.
 *
 * FRED serves every series as CSV from `fredgraph.csv` with no API key, so the
 * dashboard reads that endpoint directly and derives its axes from the returned
 * observations.
 */

export type Point = { label: string; value: number };

/** Static description of a series — everything that does not depend on the data. */
export type SeriesSpec = {
  /** FRED series ID, e.g. "CPALTT01USM657N". */
  id: string;
  /** Card heading above the chart frame. */
  title: string;
  /** Legend text next to the coloured line, matching FRED's series name. */
  legend: string;
  /** Rotated caption on the y axis. */
  yLabel: string;
};

/** Everything derived from the observations FRED returned. */
export type SeriesData = {
  points: Point[];
  domain: [number, number];
  yTicks: number[];
  /** Decimal places for y-axis ticks and tooltips. */
  decimals: number;
  /** Subset of point labels rendered as x-axis ticks. */
  xTicks: string[];
  /** Grey "shaded areas indicate U.S. recessions" band, when it falls in range. */
  recession?: { from: string; to: string };
  /** Draw a heavy line at zero, as FRED does for series that cross it. */
  zeroLine: boolean;
};

export const SERIES: SeriesSpec[] = [
  {
    id: "CPALTT01USM657N",
    title: "CPI - last five years",
    legend: "Consumer Price Index: All Items: Total for United States",
    yLabel: "Growth rate previous period",
  },
  {
    id: "LRUN64TTUSQ156S",
    title: "Infra-Annual Labor Statistics: Unemployment Rate Total",
    legend:
      "Infra-Annual Labor Statistics: Unemployment Rate Total: From 15 to 64 Years for United States",
    yLabel: "Percent",
  },
  {
    id: "IRLTLT01USM156N",
    title: "Interest Rates: Long-Term Government Bond Yields: 10-Year",
    legend:
      "Interest Rates: Long-Term Government Bond Yields: 10-Year: Main (Including Benchmark) for United States",
    yLabel: "Percent",
  },
  {
    id: "IR3TIB01USM156N",
    title: "Interest Rates: 3-Month or 90-Day Rates and Yields",
    legend:
      "Interest Rates: 3-Month or 90-Day Rates and Yields: Interbank Rates: Total for United States",
    yLabel: "Percent",
  },
];

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** The only NBER recession overlapping the recent window (Feb–Apr 2020). */
const RECESSION = { start: Date.UTC(2020, 1, 1), end: Date.UTC(2020, 3, 1) };

/** How much history each chart shows. */
const WINDOW_YEARS = 5;

type Observation = { date: Date; value: number };

/**
 * FRED's CSV is `observation_date,VALUE` with "." marking a missing reading.
 */
function parseCsv(csv: string): Observation[] {
  return csv
    .trim()
    .split("\n")
    .slice(1)
    .map((line) => {
      const [date, raw] = line.split(",");
      return { date: new Date(`${date.trim()}T00:00:00Z`), value: Number(raw) };
    })
    .filter((o) => !Number.isNaN(o.value) && !Number.isNaN(o.date.getTime()));
}

/** Monthly and quarterly series need different labels and tick cadences. */
function detectFrequency(observations: Observation[]): "monthly" | "quarterly" {
  if (observations.length < 2) return "monthly";
  const days =
    (observations[1].date.getTime() - observations[0].date.getTime()) / 86_400_000;
  return days > 45 ? "quarterly" : "monthly";
}

function formatLabel(date: Date, frequency: "monthly" | "quarterly"): string {
  const year = date.getUTCFullYear();
  if (frequency === "quarterly") {
    return `Q${Math.floor(date.getUTCMonth() / 3) + 1} ${year}`;
  }
  return `${MONTHS[date.getUTCMonth()]} ${year}`;
}

/**
 * Picks a round axis step so the domain lands on whole gridlines, the way FRED
 * draws them — e.g. a -0.65…1.40 range becomes -1.0…1.5 in steps of 0.5.
 */
function niceAxis(min: number, max: number): {
  domain: [number, number];
  ticks: number[];
  decimals: number;
} {
  const targetTicks = 6;
  const span = max - min || 1;
  const rough = span / targetTicks;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step =
    [1, 2, 2.5, 5, 10].find((m) => magnitude * m >= rough)! * magnitude;

  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const decimals = Math.max(0, -Math.floor(Math.log10(step)));

  const ticks: number[] = [];
  // Accumulate on integers to avoid floating point drift on fractional steps.
  for (let i = 0; lo + i * step <= hi + step / 1000; i++) {
    ticks.push(Number((lo + i * step).toFixed(decimals + 1)));
  }
  return { domain: [lo, hi], ticks, decimals };
}

/**
 * Chooses an x-tick cadence of at most ~12 labels, anchored to calendar
 * boundaries so ticks land on January/July rather than arbitrary months.
 */
function pickXTicks(
  observations: Observation[],
  labels: string[],
  frequency: "monthly" | "quarterly",
): string[] {
  const candidates = frequency === "quarterly" ? [1, 2, 4, 8] : [1, 2, 3, 4, 6, 12];
  const step =
    candidates.find((s) => observations.length / s <= 12) ??
    candidates[candidates.length - 1];

  const first = observations[0].date;
  const unit =
    frequency === "quarterly"
      ? Math.floor(first.getUTCMonth() / 3)
      : first.getUTCMonth();
  const offset = (step - (unit % step)) % step;

  return labels.filter((_, i) => i >= offset && (i - offset) % step === 0);
}

/** Fetches one series and derives everything the chart card needs. */
export async function loadSeries(spec: SeriesSpec): Promise<SeriesData> {
  const res = await fetch(
    `https://fred.stlouisfed.org/graph/fredgraph.csv?id=${spec.id}`,
    // FRED updates these series at most daily; cache between rebuilds.
    { cache: "force-cache", next: { revalidate: 43_200 } },
  );
  if (!res.ok) {
    throw new Error(`FRED ${spec.id} responded ${res.status} ${res.statusText}`);
  }

  const all = parseCsv(await res.text());
  if (all.length === 0) throw new Error(`FRED ${spec.id} returned no observations`);

  // Show the last WINDOW_YEARS of whatever the series actually covers, so a
  // discontinued series still ends on its own final observation.
  const latest = all[all.length - 1].date;
  const cutoff = Date.UTC(
    latest.getUTCFullYear() - WINDOW_YEARS,
    latest.getUTCMonth(),
    latest.getUTCDate(),
  );
  const observations = all.filter((o) => o.date.getTime() > cutoff);

  const frequency = detectFrequency(observations);
  const labels = observations.map((o) => formatLabel(o.date, frequency));
  const values = observations.map((o) => o.value);

  const { domain, ticks, decimals } = niceAxis(
    Math.min(...values),
    Math.max(...values),
  );

  // Shade the recession only where it overlaps the visible window.
  const inWindow = observations.filter(
    (o) => o.date.getTime() >= RECESSION.start && o.date.getTime() <= RECESSION.end,
  );
  const recession =
    inWindow.length > 1
      ? {
          from: formatLabel(inWindow[0].date, frequency),
          to: formatLabel(inWindow[inWindow.length - 1].date, frequency),
        }
      : undefined;

  return {
    points: labels.map((label, i) => ({ label, value: values[i] })),
    domain,
    yTicks: ticks,
    decimals,
    xTicks: pickXTicks(observations, labels, frequency),
    recession,
    zeroLine: domain[0] < 0 && domain[1] > 0,
  };
}
