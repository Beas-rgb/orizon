import { AnimatePresence, motion } from "motion/react";
import {
  Archive,
  BarChart2,
  Bell,
  Briefcase,
  ChevronRight,
  ClipboardList,
  Clock,
  FileText,
  HelpCircle,
  LayoutDashboard,
  Settings,
  Star,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { ACCENT } from "../../lib/theme";

type Item = {
  icon: typeof LayoutDashboard;
  label: string;
  active?: boolean;
  badge?: string | null;
  onClick?: () => void;
};

type Section = { title: string; items: Item[] };

type Props = {
  open: boolean;
  onClose: () => void;
  nome: string;
  papelLabel: string;
  sections: Section[];
};

export function Sidebar({ open, onClose, nome, papelLabel, sections }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40"
            style={{ background: "rgba(20,30,50,0.20)", backdropFilter: "blur(3px)" }}
          />
          <motion.div
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed left-0 top-0 bottom-0 z-50 w-[min(18rem,88vw)] flex flex-col overflow-hidden"
            style={{
              background: "rgba(240,244,250,0.88)",
              backdropFilter: "blur(40px) saturate(180%)",
              WebkitBackdropFilter: "blur(40px) saturate(180%)",
              borderRight: "1px solid rgba(255,255,255,0.55)",
              boxShadow: "6px 0 30px rgba(0,0,0,0.12)",
            }}
          >
            <div
              className="flex items-center justify-between p-5 pb-4"
              style={{ borderBottom: "1px solid rgba(0,0,0,0.07)" }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-2xl flex items-center justify-center"
                  style={{
                    background: `linear-gradient(135deg, ${ACCENT}, #164A8A)`,
                    boxShadow: "0 3px 10px rgba(29,95,175,0.30)",
                  }}
                >
                  <span className="text-white text-sm font-bold">OR</span>
                </div>
                <div>
                  <p className="text-gray-800 text-sm font-bold">Orizon</p>
                  <p className="text-gray-500 text-[11px]">Menu</p>
                </div>
              </div>
              <button type="button" onClick={onClose} className="p-1.5 rounded-xl hover:bg-black/5">
                <X size={16} className="text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              {sections.map((section) => (
                <div key={section.title} className="mb-5">
                  <p className="px-3 mb-2 text-gray-400 uppercase tracking-widest text-[10px] font-semibold">
                    {section.title}
                  </p>
                  {section.items.map((item) => (
                    <motion.button
                      key={item.label}
                      type="button"
                      whileHover={{ x: 3 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        item.onClick?.();
                        onClose();
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl mb-0.5 text-left group"
                      style={{
                        background: item.active ? "rgba(29,95,175,0.12)" : "transparent",
                        border: item.active
                          ? "1px solid rgba(29,95,175,0.22)"
                          : "1px solid transparent",
                      }}
                    >
                      <div
                        className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                        style={{
                          background: item.active ? "rgba(29,95,175,0.16)" : "rgba(0,0,0,0.05)",
                        }}
                      >
                        <item.icon size={15} style={{ color: item.active ? ACCENT : "#6b7280" }} />
                      </div>
                      <span
                        className="flex-1 text-[13px]"
                        style={{
                          fontWeight: item.active ? 700 : 400,
                          color: item.active ? ACCENT : "#4b5563",
                        }}
                      >
                        {item.label}
                      </span>
                      {item.badge ? (
                        <span
                          className="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
                          style={{
                            background: item.active ? "rgba(29,95,175,0.16)" : "rgba(0,0,0,0.07)",
                            color: item.active ? ACCENT : "#6b7280",
                          }}
                        >
                          {item.badge}
                        </span>
                      ) : null}
                      <ChevronRight
                        size={12}
                        className="text-gray-300 opacity-0 group-hover:opacity-100"
                      />
                    </motion.button>
                  ))}
                </div>
              ))}
            </div>

            <div className="p-4" style={{ borderTop: "1px solid rgba(0,0,0,0.07)" }}>
              <div
                className="flex items-center gap-3 p-3 rounded-2xl"
                style={{
                  background: "rgba(255,255,255,0.55)",
                  border: "1px solid rgba(255,255,255,0.7)",
                }}
              >
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-sm font-bold"
                  style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
                >
                  {nome.slice(0, 1).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-800 truncate text-[13px] font-semibold">{nome}</p>
                  <p className="text-gray-500 truncate text-[11px]">{papelLabel}</p>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export const iconMap = {
  LayoutDashboard,
  Briefcase,
  ClipboardList,
  BarChart2,
  TrendingUp,
  Users,
  FileText,
  Archive,
  Clock,
  Star,
  Bell,
  Settings,
  HelpCircle,
};
