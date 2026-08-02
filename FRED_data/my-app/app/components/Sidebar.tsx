import {
  Briefcase,
  ChevronDown,
  ChevronRight,
  Globe,
  Home,
  LineChart,
  ShoppingCart,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

type NavItem = { label: string; icon: LucideIcon };

const NAV: NavItem[] = [
  { label: "Key Indicators", icon: TrendingUp },
  { label: "Inflation", icon: TrendingUp },
  { label: "Employment", icon: Briefcase },
  { label: "Interest Rates", icon: LineChart },
  { label: "Economic Growth", icon: TrendingUp },
  { label: "Exchange Rates", icon: Globe },
  { label: "Housing", icon: Home },
  { label: "Consumer Spending", icon: ShoppingCart },
];

export default function Sidebar() {
  return (
    <aside className="flex w-[272px] shrink-0 flex-col border-r border-[#eaebee] bg-white">
      <div className="border-b border-[#eaebee] px-5 py-5">
        <p className="text-xl font-bold text-[#121826]">FRED Indicators</p>
        <p className="mt-1 text-sm text-[#5f6772]">Economic Data Dashboard</p>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {NAV.map(({ label, icon: Icon }, i) => {
          const active = i === 0;
          return (
            <a
              key={label}
              href="#"
              aria-current={active ? "page" : undefined}
              className={`flex h-[38px] items-center gap-3 rounded-lg px-3 text-[15px] ${
                active
                  ? "bg-[#3370b4] font-semibold text-white"
                  : "text-[#374151] hover:bg-[#f3f4f6]"
              }`}
            >
              <Icon className="size-[18px] shrink-0" strokeWidth={2} />
              <span className="truncate">{label}</span>
              {active ? (
                <ChevronDown className="ml-auto size-4 shrink-0" />
              ) : (
                <ChevronRight className="ml-auto size-4 shrink-0 text-[#9ca3af]" />
              )}
            </a>
          );
        })}
      </nav>

      <div className="border-t border-[#eaebee] px-4 py-4">
        <p className="text-xs leading-5 text-[#6b7280]">
          Data provided by Federal Reserve Economic Data (FRED)
        </p>
      </div>
    </aside>
  );
}
