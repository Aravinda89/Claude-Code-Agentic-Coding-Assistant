import FredChartCard from "./components/FredChartCard";
import Sidebar from "./components/Sidebar";
import { loadSeries, SERIES, type SeriesData } from "./lib/fred";

// FRED publishes these series at most once a day.
export const revalidate = 43_200;

export default async function Home() {
  // A single unavailable series should not blank out the whole dashboard.
  const results = await Promise.allSettled(SERIES.map(loadSeries));

  const charts = SERIES.map((spec, i) => {
    const result = results[i];
    if (result.status === "rejected") {
      console.error(`Failed to load ${spec.id} from FRED:`, result.reason);
      return { spec, data: null as SeriesData | null };
    }
    return { spec, data: result.value };
  });

  return (
    <div className="flex flex-1 overflow-hidden bg-white">
      <Sidebar />

      <main className="flex-1 overflow-y-auto bg-[#f3f4f6] px-8 py-8">
        <h1 className="text-[30px] font-bold leading-tight text-[#121826]">
          Economic Indicators Dashboard
        </h1>
        <p className="mt-2 text-base text-[#5f6772]">
          Real-time economic data from the Federal Reserve Economic Data (FRED)
          system
        </p>

        <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
          {charts.map(({ spec, data }) => (
            <FredChartCard key={spec.id} spec={spec} data={data} />
          ))}
        </div>
      </main>
    </div>
  );
}
