import {
  FC,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import {
  definePlugin,
  call,
  toaster,
} from "@decky/api";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  Focusable,
  Spinner,
} from "@decky/ui";
import {
  FaCloudUploadAlt,
  FaSyncAlt,
  FaCheckCircle,
  FaPlus,
  FaTimes,
  FaExclamationTriangle,
  FaFolderMinus,
  FaDownload,
  FaChevronDown,
  FaChevronRight,
  FaGamepad,
} from "react-icons/fa";

// ==========================================
// Types
// ==========================================

interface HoardUserInfo {
  kind?: "cloud" | "self_host";
  email?: string;
  plan?: string;
  username?: string;
  server?: string;
}

interface HoardStatus {
  installed: boolean;
  version: string | null;
  logged_in: boolean;
  user_info: HoardUserInfo | null;
  service_running: boolean;
  is_scanning: boolean;
  binary_path: string;
}

interface GameItem {
  name: string;
  slug: string;
  save_id: string | null;
  paused: boolean;
  last_version_num: number | null;
  last_backup_at: string | null;
  needs_folder: boolean;
  paths: string[];
  tracked: boolean;
}

interface GamesData {
  ready_to_track: GameItem[];
  tracked: GameItem[];
  missing_folder: GameItem[];
  summary: {
    total: number;
    ready_count: number;
    tracked_count: number;
    missing_count: number;
  };
}

// ==========================================
// i18n Localization
// ==========================================

const getLanguage = (): "fr" | "en" => {
  try {
    const steamLang = (window as any).SteamClient?.Settings?.GetCurrentLanguage?.()?.toLowerCase();
    if (steamLang === "french" || steamLang === "fr") return "fr";
  } catch {}
  return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
};

const STRINGS = {
  en: {
    pluginTitle: "Hoard Sync",
    notInstalledTitle: "Hoard is Not Installed",
    notInstalledDesc: "Hoard CLI is required to backup and sync your game saves across devices.",
    installBtn: "Install Hoard CLI",
    installing: "Downloading & Installing...",
    installSuccess: "Hoard installed successfully!",
    installFailed: "Installation failed: ",
    sessionRequiredTitle: "Sign-in Required",
    sessionRequiredDesc: "Run 'hoard login' once in Desktop Mode to link your account or server.",
    syncSection: "Service & Sync",
    syncNow: "Sync Now",
    syncing: "Synchronizing...",
    syncSuccess: "Saves synchronized!",
    syncFailed: "Sync failed: ",
    refreshBtn: "Refresh Library",
    scanning: "Scanning games...",
    daemonActive: "Sync daemon active",
    daemonInactive: "Sync daemon stopped",
    readySection: "Ready to Track",
    trackedSection: "Tracked Games",
    missingFolderSection: "Save Folder Missing",
    missingFolderDesc: "Installed but no save folder located on this device yet.",
    trackSuccess: "now tracked!",
    trackFailed: "Could not track game: ",
    untrackSuccess: "untracked locally.",
    untrackFailed: "Could not untrack: ",
    emptyCategory: "No games in this section",
    collapse: "Collapse",
    expand: "Expand",
  },
  fr: {
    pluginTitle: "Hoard Sync",
    notInstalledTitle: "Hoard n'est pas installé",
    notInstalledDesc: "La CLI Hoard est requise pour sauvegarder et synchroniser vos sauvegardes.",
    installBtn: "Installer Hoard CLI",
    installing: "Téléchargement & Installation...",
    installSuccess: "Hoard installé avec succès !",
    installFailed: "Échec de l'installation : ",
    sessionRequiredTitle: "Connexion requise",
    sessionRequiredDesc: "Lancez 'hoard login' une fois en Mode Bureau pour lier votre compte ou serveur.",
    syncSection: "Service & Synchronisation",
    syncNow: "Synchroniser maintenant",
    syncing: "Synchronisation...",
    syncSuccess: "Sauvegardes synchronisées !",
    syncFailed: "Échec de la synchronisation : ",
    refreshBtn: "Rafraîchir la bibliothèque",
    scanning: "Analyse des jeux...",
    daemonActive: "Démon de synchronisation actif",
    daemonInactive: "Démon de synchronisation arrêté",
    readySection: "Prêts à être suivis",
    trackedSection: "Jeux suivis",
    missingFolderSection: "Dossier de sauvegarde introuvable",
    missingFolderDesc: "Installé mais aucun dossier de sauvegarde trouvé sur cet appareil.",
    trackSuccess: "est maintenant suivi !",
    trackFailed: "Impossible de suivre le jeu : ",
    untrackSuccess: "n'est plus suivi localement.",
    untrackFailed: "Impossible d'arrêter le suivi : ",
    emptyCategory: "Aucun jeu dans cette section",
    collapse: "Réduire",
    expand: "Développer",
  },
};

// ==========================================
// Badge UI Helper
// ==========================================

const Badge: FC<{ children: ReactNode; color?: "green" | "amber" | "blue" | "gray" }> = ({
  children,
  color = "blue",
}) => {
  const styles: Record<string, { bg: string; text: string; border: string }> = {
    green: {
      bg: "rgba(46, 204, 113, 0.15)",
      text: "#2ecc71",
      border: "rgba(46, 204, 113, 0.35)",
    },
    amber: {
      bg: "rgba(241, 196, 15, 0.15)",
      text: "#f1c40f",
      border: "rgba(241, 196, 15, 0.35)",
    },
    blue: {
      bg: "rgba(52, 152, 219, 0.15)",
      text: "#3498db",
      border: "rgba(52, 152, 219, 0.35)",
    },
    gray: {
      bg: "rgba(189, 195, 199, 0.12)",
      text: "#bdc3c7",
      border: "rgba(189, 195, 199, 0.25)",
    },
  };

  const current = styles[color] || styles.blue;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "10px",
        fontSize: "11px",
        fontWeight: "bold",
        backgroundColor: current.bg,
        color: current.text,
        border: `1px solid ${current.border}`,
        marginLeft: "6px",
        flexShrink: 0,
      }}
    >
      {children}
    </span>
  );
};

// ==========================================
// Main Plugin Content Component
// ==========================================

const HoardContent: FC = () => {
  const lang = useMemo(() => getLanguage(), []);
  const t = STRINGS[lang];

  const [status, setStatus] = useState<HoardStatus | null>(null);
  const [games, setGames] = useState<GamesData | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(true);
  const [isLoadingGames, setIsLoadingGames] = useState<boolean>(false);
  const [isInstalling, setIsInstalling] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [busyGame, setBusyGame] = useState<string | null>(null);
  const [showMissingFolder, setShowMissingFolder] = useState<boolean>(false);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoadingStatus(true);
      const res = await call<[], HoardStatus>("get_status");
      setStatus(res);
      return res;
    } catch (e) {
      console.error("Failed to get Hoard status", e);
      return null;
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  const fetchGames = useCallback(async (forceRefresh = false) => {
    try {
      setIsLoadingGames(true);
      const res = await call<[boolean], GamesData>("get_games", forceRefresh);
      setGames(res);
    } catch (e) {
      console.error("Failed to load games list", e);
    } finally {
      setIsLoadingGames(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus().then((s) => {
      if (s?.installed) {
        fetchGames(false);
      }
    });
  }, [fetchStatus, fetchGames]);

  const handleInstall = async () => {
    setIsInstalling(true);
    toaster.toast({ title: t.pluginTitle, body: t.installing, duration: 4000 });

    try {
      const res = await call<[], { ok: boolean; message: string }>("install_hoard");
      if (res.ok) {
        toaster.toast({ title: t.pluginTitle, body: t.installSuccess, duration: 3000 });
        await fetchStatus();
        fetchGames(true);
      } else {
        toaster.toast({ title: t.pluginTitle, body: `${t.installFailed}${res.message}`, duration: 5000 });
      }
    } catch (err: any) {
      toaster.toast({ title: t.pluginTitle, body: `${t.installFailed}${err?.message || err}`, duration: 5000 });
    } finally {
      setIsInstalling(false);
    }
  };

  const handleSyncNow = async () => {
    setIsSyncing(true);
    toaster.toast({ title: t.pluginTitle, body: t.syncing, duration: 3000 });

    try {
      const res = await call<[], { ok: boolean; message: string }>("force_sync");
      if (res.ok) {
        toaster.toast({ title: t.pluginTitle, body: res.message || t.syncSuccess, duration: 3000 });
        fetchStatus();
        fetchGames(true);
      } else {
        toaster.toast({ title: t.pluginTitle, body: `${t.syncFailed}${res.message}`, duration: 5000 });
      }
    } catch (err: any) {
      toaster.toast({ title: t.pluginTitle, body: `${t.syncFailed}${err?.message || err}`, duration: 5000 });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleTrack = async (game: GameItem) => {
    setBusyGame(game.slug);
    try {
      const res = await call<[string, string | null], { ok: boolean; message: string }>(
        "track_game",
        game.name,
        game.slug
      );
      if (res.ok) {
        toaster.toast({ title: t.pluginTitle, body: `"${game.name}" ${t.trackSuccess}`, duration: 3000 });
        fetchGames(true);
      } else {
        toaster.toast({ title: t.pluginTitle, body: `${t.trackFailed}${res.message}`, duration: 5000 });
      }
    } catch (err: any) {
      toaster.toast({ title: t.pluginTitle, body: `${t.trackFailed}${err?.message || err}`, duration: 5000 });
    } finally {
      setBusyGame(null);
    }
  };

  const handleUntrack = async (game: GameItem) => {
    if (!game.save_id) return;
    setBusyGame(game.slug);
    try {
      const res = await call<[string], { ok: boolean; message: string }>("untrack_game", game.save_id);
      if (res.ok) {
        toaster.toast({ title: t.pluginTitle, body: `"${game.name}" ${t.untrackSuccess}`, duration: 3000 });
        fetchGames(true);
      } else {
        toaster.toast({ title: t.pluginTitle, body: `${t.untrackFailed}${res.message}`, duration: 5000 });
      }
    } catch (err: any) {
      toaster.toast({ title: t.pluginTitle, body: `${t.untrackFailed}${err?.message || err}`, duration: 5000 });
    } finally {
      setBusyGame(null);
    }
  };

  if (isLoadingStatus && !status) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "center", padding: "24px" }}>
            <Spinner />
          </div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  if (!status?.installed) {
    return (
      <PanelSection title={t.notInstalledTitle}>
        <PanelSectionRow>
          <div
            style={{
              padding: "12px",
              backgroundColor: "rgba(231, 76, 60, 0.12)",
              borderRadius: "8px",
              border: "1px solid rgba(231, 76, 60, 0.3)",
              marginBottom: "12px",
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
            }}
          >
            <FaExclamationTriangle style={{ color: "#e74c3c", fontSize: "20px", marginTop: "2px", flexShrink: 0 }} />
            <div style={{ fontSize: "13px", lineHeight: "1.4" }}>{t.notInstalledDesc}</div>
          </div>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleInstall} disabled={isInstalling}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isInstalling ? <Spinner /> : <FaDownload />}
              <span>{isInstalling ? t.installing : t.installBtn}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  const accountLabel =
    status.user_info?.email ||
    (status.user_info?.username ? `${status.user_info.username}` : null);

  return (
    <>
      <PanelSection title={t.syncSection}>
        {!status.logged_in && (
          <PanelSectionRow>
            <div
              style={{
                padding: "10px",
                backgroundColor: "rgba(241, 196, 15, 0.12)",
                borderRadius: "8px",
                border: "1px solid rgba(241, 196, 15, 0.35)",
                marginBottom: "10px",
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
              }}
            >
              <FaExclamationTriangle style={{ color: "#f1c40f", fontSize: "18px", marginTop: "2px", flexShrink: 0 }} />
              <div style={{ fontSize: "12px", lineHeight: "1.4" }}>
                <strong>{t.sessionRequiredTitle}:</strong> {t.sessionRequiredDesc}
              </div>
            </div>
          </PanelSectionRow>
        )}

        <PanelSectionRow>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
              padding: "4px 0",
              fontSize: "13px",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span>{status.service_running ? t.daemonActive : t.daemonInactive}</span>
              {accountLabel && (
                <span style={{ fontSize: "11px", color: "#888" }}>{accountLabel}</span>
              )}
            </div>
            <Badge color={status.service_running ? "green" : "gray"}>
              {status.service_running ? "ONLINE" : "OFFLINE"}
            </Badge>
          </div>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleSyncNow} disabled={isSyncing}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isSyncing ? <Spinner /> : <FaSyncAlt />}
              <span>{isSyncing ? t.syncing : t.syncNow}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => fetchGames(true)} disabled={isLoadingGames}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isLoadingGames ? <Spinner /> : <FaGamepad />}
              <span>{isLoadingGames ? t.scanning : t.refreshBtn}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      {isLoadingGames && !games && (
        <PanelSection>
          <PanelSectionRow>
            <div style={{ display: "flex", justifyContent: "center", padding: "16px" }}>
              <Spinner />
            </div>
          </PanelSectionRow>
        </PanelSection>
      )}

      {games && (
        <>
          {/* Section 1: Tracked Games */}
          <PanelSection title={`${t.trackedSection} (${games.summary.tracked_count})`}>
            {games.tracked.length === 0 ? (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }}>
                  {t.emptyCategory}
                </div>
              </PanelSectionRow>
            ) : (
              games.tracked.map((game) => {
                const isBusy = busyGame === game.slug;
                const verLabel = game.last_version_num ? `v${game.last_version_num}` : "SYNCED";
                return (
                  <PanelSectionRow key={game.slug}>
                    <ButtonItem
                      layout="below"
                      description={game.slug}
                      onClick={() => handleUntrack(game)}
                      disabled={isBusy || !game.save_id}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                          <FaCheckCircle style={{ color: "#2ecc71", fontSize: "13px", flexShrink: 0 }} />
                          <span style={{ fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {game.name}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
                          <Badge color={game.paused ? "amber" : "green"}>
                            {game.paused ? "PAUSED" : verLabel}
                          </Badge>
                          {isBusy ? <Spinner /> : game.save_id ? <FaTimes style={{ color: "#888", fontSize: "11px" }} /> : null}
                        </div>
                      </div>
                    </ButtonItem>
                  </PanelSectionRow>
                );
              })
            )}
          </PanelSection>

          {/* Section 2: Ready to track */}
          <PanelSection title={`${t.readySection} (${games.summary.ready_count})`}>
            {games.ready_to_track.length === 0 ? (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }}>
                  {t.emptyCategory}
                </div>
              </PanelSectionRow>
            ) : (
              games.ready_to_track.map((game) => {
                const isBusy = busyGame === game.slug;
                return (
                  <PanelSectionRow key={game.slug}>
                    <ButtonItem
                      layout="below"
                      description={game.slug}
                      onClick={() => handleTrack(game)}
                      disabled={isBusy}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }}>
                        <span style={{ fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {game.name}
                        </span>
                        {isBusy ? <Spinner /> : <FaPlus style={{ color: "#3498db", flexShrink: 0 }} />}
                      </div>
                    </ButtonItem>
                  </PanelSectionRow>
                );
              })
            )}
          </PanelSection>

          {/* Section 3: Missing save folder (collapsed by default) */}
          {games.summary.missing_count > 0 && (
            <PanelSection title={`${t.missingFolderSection} (${games.summary.missing_count})`}>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={() => setShowMissingFolder((prev) => !prev)}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                    {showMissingFolder ? <FaChevronDown /> : <FaChevronRight />}
                    <span>{showMissingFolder ? t.collapse : t.expand} ({games.summary.missing_count})</span>
                  </div>
                </ButtonItem>
              </PanelSectionRow>

              {showMissingFolder && (
                <>
                  <PanelSectionRow>
                    <div style={{ fontSize: "11px", color: "#888", marginBottom: "6px" }}>
                      {t.missingFolderDesc}
                    </div>
                  </PanelSectionRow>
                  {games.missing_folder.map((game) => (
                    <PanelSectionRow key={game.slug}>
                      <Focusable
                        onActivate={() => {}}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          width: "100%",
                          padding: "6px 8px",
                          borderRadius: "4px",
                          opacity: 0.6,
                          backgroundColor: "rgba(0, 0, 0, 0.15)",
                        }}
                      >
                        <FaFolderMinus style={{ color: "#f39c12", fontSize: "14px", flexShrink: 0 }} />
                        <span
                          style={{
                            fontSize: "12px",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                          }}
                        >
                          {game.name}
                        </span>
                      </Focusable>
                    </PanelSectionRow>
                  ))}
                </>
              )}
            </PanelSection>
          )}
        </>
      )}
    </>
  );
};

export default definePlugin(() => {
  return {
    name: "Hoard Sync",
    icon: <FaCloudUploadAlt />,
    content: <HoardContent />,
    onDismount() {},
  };
});
