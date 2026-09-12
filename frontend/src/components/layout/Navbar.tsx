import { AnimatePresence, motion } from "motion/react";
import { Bell, ChevronDown, Command, Search, Settings, X } from "lucide-react";
import { useState } from "react";
import { ACCENT, dropdownStyle, iniciais } from "../../lib/theme";

type Props = {
  nome: string;
  papelLabel: string;
  onMenuClick: () => void;
  onSair: () => void;
  searchHints?: { type: string; label: string; icon: string }[];
};

export function Navbar({
  nome,
  papelLabel,
  onMenuClick,
  onSair,
  searchHints = [],
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const filtered = searchHints.filter(
    (s) =>
      searchQuery.length > 0 && s.label.toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const showDropdown =
    searchFocused && (searchQuery.length > 0 ? filtered.length > 0 : searchHints.length > 0);

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center px-3 sm:px-4 py-2 gap-2 sm:gap-3"
      style={{
        background: "rgba(238,242,248,0.80)",
        backdropFilter: "blur(24px) saturate(170%)",
        WebkitBackdropFilter: "blur(24px) saturate(170%)",
        borderBottom: "1px solid rgba(255,255,255,0.55)",
        boxShadow: "0 1px 12px rgba(0,0,0,0.08)",
        height: "60px",
      }}
    >
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 sm:min-w-[160px]">
        <button
          type="button"
          onClick={onMenuClick}
          className="flex flex-col gap-[5px] p-2 rounded-xl hover:bg-white/45 active:scale-95"
          aria-label="Abrir menu"
        >
          <span className="block w-5 h-[2px] bg-gray-600 rounded-full" />
          <span className="block w-5 h-[2px] bg-gray-600 rounded-full" />
          <span className="block w-5 h-[2px] bg-gray-600 rounded-full" />
        </button>
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
            style={{
              background: `linear-gradient(135deg, ${ACCENT}, #164A8A)`,
              boxShadow: "0 2px 8px rgba(29,95,175,0.30)",
            }}
          >
            <span className="text-white text-xs font-bold">OR</span>
          </div>
          <div className="hidden sm:block min-w-0">
            <p className="text-gray-800 leading-none text-[13px] font-bold">Orizon</p>
            <p className="text-gray-500 leading-none text-[10px] truncate">{papelLabel}</p>
          </div>
        </div>
      </div>

      <div className="hidden sm:block flex-1 max-w-xl mx-auto relative min-w-0">
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-2xl transition-all duration-300"
          style={{
            background: searchFocused ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.55)",
            border: searchFocused
              ? "1px solid rgba(29,95,175,0.35)"
              : "1px solid rgba(255,255,255,0.6)",
            boxShadow: searchFocused
              ? "0 0 0 3px rgba(29,95,175,0.10), 0 4px 16px rgba(0,0,0,0.08)"
              : "0 1px 6px rgba(0,0,0,0.05)",
          }}
        >
          <Search size={15} className="text-gray-400 shrink-0" />
          <input
            type="search"
            placeholder="Buscar trabalhos, páginas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setTimeout(() => setSearchFocused(false), 150)}
            className="flex-1 bg-transparent outline-none text-gray-700 placeholder-gray-400 text-[13px] min-w-0"
          />
          {searchQuery ? (
            <button type="button" onClick={() => setSearchQuery("")} aria-label="Limpar">
              <X size={13} className="text-gray-400" />
            </button>
          ) : (
            <div
              className="hidden md:flex items-center gap-1 px-1.5 py-0.5 rounded-md"
              style={{ background: "rgba(0,0,0,0.05)", border: "1px solid rgba(0,0,0,0.08)" }}
            >
              <Command size={10} className="text-gray-400" />
              <span className="text-gray-400 text-[10px]">K</span>
            </div>
          )}
        </div>

        <AnimatePresence>
          {showDropdown && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 4, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              className="absolute left-0 right-0 top-full rounded-2xl overflow-hidden z-50"
              style={dropdownStyle}
            >
              <div className="p-2 max-h-64 overflow-y-auto">
                {(searchQuery.length > 0 ? filtered : searchHints).map((item) => (
                  <div
                    key={item.label}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/80 text-left"
                  >
                    <span className="text-base">{item.icon}</span>
                    <div>
                      <p className="text-gray-800 text-[13px]">{item.label}</p>
                      <p className="text-gray-400 text-[11px]">{item.type}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-1 sm:gap-2 justify-end shrink-0">
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowNotifications(!showNotifications);
              setShowProfile(false);
            }}
            className="relative p-2 rounded-xl hover:bg-white/45"
            aria-label="Notificações"
          >
            <Bell size={18} className="text-gray-600" />
          </button>
          <AnimatePresence>
            {showNotifications && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.95 }}
                animate={{ opacity: 1, y: 4, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.95 }}
                className="absolute right-0 top-full w-72 rounded-2xl overflow-hidden z-50"
                style={dropdownStyle}
              >
                <div className="p-4">
                  <p className="text-gray-800 mb-2 text-[13px] font-bold">Notificações</p>
                  <p className="text-gray-500 text-[12px]">Avisos do seu painel aparecem aqui.</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button type="button" className="hidden sm:block p-2 rounded-xl hover:bg-white/45" aria-label="Configurações">
          <Settings size={18} className="text-gray-600" />
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowProfile(!showProfile);
              setShowNotifications(false);
            }}
            className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-xl hover:bg-white/45"
          >
            <div
              className="w-7 h-7 rounded-xl flex items-center justify-center text-white text-xs font-bold"
              style={{
                background: `linear-gradient(135deg, ${ACCENT}, #164A8A)`,
                boxShadow: "0 2px 6px rgba(29,95,175,0.28)",
              }}
            >
              {iniciais(nome).slice(0, 1)}
            </div>
            <span className="hidden sm:inline text-gray-700 text-[12px] font-semibold max-w-[80px] truncate">
              {nome.split(" ")[0]}
            </span>
            <ChevronDown size={12} className="text-gray-500 hidden sm:block" />
          </button>
          <AnimatePresence>
            {showProfile && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.95 }}
                animate={{ opacity: 1, y: 4, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.95 }}
                className="absolute right-0 top-full w-52 rounded-2xl overflow-hidden z-50"
                style={dropdownStyle}
              >
                <div className="p-3">
                  <div className="flex items-center gap-3 p-2 mb-2">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold"
                      style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
                    >
                      {iniciais(nome).slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-gray-800 text-[13px] font-semibold truncate">{nome}</p>
                      <p className="text-gray-500 text-[11px]">{papelLabel}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={onSair}
                    className="w-full text-left px-3 py-2 rounded-xl hover:bg-white/80 text-[13px]"
                    style={{ color: "#A02828" }}
                  >
                    Sair
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </nav>
  );
}
