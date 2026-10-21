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

interface HoardStatus {
  installed: boolean;
  version: string | null;
  logged_in: boolean;
  user_info: any;
  service_running: boolean;
  is_scanning: boolean;
  binary_path: string;
}

interface GameItem {
  name: string;
  appid: string | null;
  slug: string | null;
  needs_folder: boolean;
  paths?: string[];
  tracked: boolean;
}

interface GamesData {
  ready_to_track: GameItem[];
  other_games: GameItem[];
  tracked: GameItem[];
  missing_folder: GameItem[];
  summary: {
    total: number;
    ready_count: number;
    other_count: number;
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
    sessionRequiredDesc: "Run 'hoard login' once in Desktop Mode to link your account or self-hosted server.",
    syncSection: "Service & Sync",
    syncNow: "Sync Now",
    syncing: "Synchronizing...",
    syncSuccess: "Saves synchronized successfully!",
    syncFailed: "Sync failed: ",
    refreshBtn: "Refresh Library",
    scanning: "Scanning games...",
    daemonActive: "Sync daemon active",
    daemonInactive: "Sync daemon stopped",
    readySection: "Ready to Track",
    otherSection: "Other Installed Games",
    trackedSection: "Tracked Games",
    missingFolderSection: "Save Folder Missing",
    missingFolderDesc: "Detected but no save folder was located on this device.",
    trackBtn: "Track",
    tracking: "Tracking...",
    trackSuccess: "now tracked!",
    trackFailed: "Could not track game: ",
    emptyCategory: "No games in this section",
    collapse: "Collapse",
    expand: "Expand",
  },
  fr: {
    pluginTitle: "Hoard Sync",
    notInstalledTitle: "Hoard n'est pas installé",
    notInstalledDesc: "La CLI Hoard est requise pour sauvegarder et synchroniser vos sauvegardes de jeux.",
    installBtn: "Installer Hoard CLI",
    installing: "Téléchargement & Installation...",
    installSuccess: "Hoard a été installé avec succès !",
    installFailed: "Échec de l'installation : ",
    sessionRequiredTitle: "Connexion requise",
    sessionRequiredDesc: "Lancez 'hoard login' une fois en Mode Bureau pour associer votre compte ou serveur.",
    syncSection: "Service & Synchronisation",
    syncNow: "Synchroniser maintenant",
    syncing: "Synchronisation...",
    syncSuccess: "Sauvegardes synchronisées avec succès !",
    syncFailed: "Échec de la synchronisation : ",
    refreshBtn: "Rafraîchir la bibliothèque",
    scanning: "Analyse des jeux...",
    daemonActive: "Démon de synchronisation actif",
    daemonInactive: "Démon de synchronisation arrêté",
    readySection: "Prêts à être suivis",
    otherSection: "Autres jeux installés",
    trackedSection: "Jeux suivis",
    missingFolderSection: "Dossier de sauvegarde introuvable",
    missingFolderDesc: "Détecté mais aucun dossier de sauvegarde trouvé sur cet appareil.",
    trackBtn: "Suivre",
    tracking: "Suivi en cours...",
    trackSuccess: "est maintenant suivi !",
    trackFailed: "Impossible de suivre le jeu : ",
    emptyCategory: "Aucun jeu dans cette section",
    collapse: "Réduire",
    expand: "Développer",
  },
};

// ==========================================
// Badges and UI helpers
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
  const [trackingGame, setTrackingGame] = useState<string | null>(null);
  const [showMissingFolder, setShowMissingFolder] = useState<boolean>(false);

  // Load Status
  const fetchStatus = useCallback(async () => {
    try {
      setIsLoadingStatus(true);
      const res = await call<[], HoardStatus>("get_status");
      setStatus(res);
      return res;
    } catch (e: any) {
      console.error("Failed to get Hoard status", e);
      return null;
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  // Load Games
  const fetchGames = useCallback(async (forceRefresh = false) => {
    try {
      setIsLoadingGames(true);
      const res = await call<[boolean], GamesData>("get_games", forceRefresh);
      setGames(res);
    } catch (e: any) {
      console.error("Failed to load games list", e);
    } finally {
      setIsLoadingGames(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchStatus().then((currentStatus) => {
      if (currentStatus?.installed) {
        fetchGames(false);
      }
    });
  }, [fetchStatus, fetchGames]);

  // Install Hoard
  const handleInstall = async () => {
    setIsInstalling(true);
    toaster.toast({
      title: t.pluginTitle,
      body: t.installing,
      duration: 4000,
    });

    try {
      const res = await call<[], { ok: boolean; message: string }>("install_hoard");
      if (res.ok) {
        toaster.toast({
          title: t.pluginTitle,
          body: t.installSuccess,
          duration: 3000,
        });
        await fetchStatus();
        fetchGames(true);
      } else {
        toaster.toast({
          title: t.pluginTitle,
          body: `${t.installFailed} ${res.message}`,
          duration: 5000,
        });
      }
    } catch (err: any) {
      toaster.toast({
        title: t.pluginTitle,
        body: `${t.installFailed} ${err?.message || err}`,
        duration: 5000,
      });
    } finally {
      setIsInstalling(false);
    }
  };

  // Sync Now
  const handleSyncNow = async () => {
    setIsSyncing(true);
    toaster.toast({
      title: t.pluginTitle,
      body: t.syncing,
      duration: 3000,
    });

    try {
      const res = await call<[], { ok: boolean; message: string }>("force_sync");
      if (res.ok) {
        toaster.toast({
          title: t.pluginTitle,
          body: t.syncSuccess,
          duration: 3000,
        });
        fetchStatus();
      } else {
        toaster.toast({
          title: t.pluginTitle,
          body: `${t.syncFailed} ${res.message}`,
          duration: 5000,
        });
      }
    } catch (err: any) {
      toaster.toast({
        title: t.pluginTitle,
        body: `${t.syncFailed} ${err?.message || err}`,
        duration: 5000,
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Track Game
  const handleTrack = async (game: GameItem) => {
    const gameIdentifier = game.slug || game.name;
    setTrackingGame(gameIdentifier);

    try {
      const res = await call<[string, string | null], { ok: boolean; message: string }>(
        "track_game",
        game.name,
        game.slug || null
      );

      if (res.ok) {
        toaster.toast({
          title: t.pluginTitle,
          body: `"${game.name}" ${t.trackSuccess}`,
          duration: 3000,
        });
        fetchGames(false);
      } else {
        toaster.toast({
          title: t.pluginTitle,
          body: `${t.trackFailed} ${res.message}`,
          duration: 5000,
        });
      }
    } catch (err: any) {
      toaster.toast({
        title: t.pluginTitle,
        body: `${t.trackFailed} ${err?.message || err}`,
        duration: 5000,
      });
    } finally {
      setTrackingGame(null);
    }
  };

  // ------------------------------------------
  // Render: Loading status initial state
  // ------------------------------------------
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

  // ------------------------------------------
  // Render: Hoard is NOT installed
  // ------------------------------------------
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
          <ButtonItem
            layout="below"
            onClick={handleInstall}
            disabled={isInstalling}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isInstalling ? <Spinner /> : <FaDownload />}
              <span>{isInstalling ? t.installing : t.installBtn}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  // ------------------------------------------
  // Render: Hoard is installed
  // ------------------------------------------
  return (
    <>
      {/* 1. Header / Status / Sync section */}
      <PanelSection title={t.syncSection}>
        {/* Session warning banner if not logged in */}
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

        {/* Daemon status info */}
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
            <span>{status.service_running ? t.daemonActive : t.daemonInactive}</span>
            <Badge color={status.service_running ? "green" : "gray"}>
              {status.service_running ? "ONLINE" : "OFFLINE"}
            </Badge>
          </div>
        </PanelSectionRow>

        {/* Sync Now button */}
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={handleSyncNow}
            disabled={isSyncing}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isSyncing ? <Spinner /> : <FaSyncAlt />}
              <span>{isSyncing ? t.syncing : t.syncNow}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>

        {/* Refresh Games button */}
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => fetchGames(true)}
            disabled={isLoadingGames}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              {isLoadingGames ? <Spinner /> : <FaGamepad />}
              <span>{isLoadingGames ? t.scanning : t.refreshBtn}</span>
            </div>
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      {/* Loading games spinner */}
      {isLoadingGames && !games && (
        <PanelSection>
          <PanelSectionRow>
            <div style={{ display: "flex", justifyContent: "center", padding: "16px" }}>
              <Spinner />
            </div>
          </PanelSectionRow>
        </PanelSection>
      )}

      {/* 2. Categorized Game List */}
      {games && (
        <>
          {/* Section 1: Ready to track */}
          <PanelSection
            title={`${t.readySection} (${games.summary.ready_count})`}
          >
            {games.ready_to_track.length === 0 ? (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }}>
                  {t.emptyCategory}
                </div>
              </PanelSectionRow>
            ) : (
              games.ready_to_track.map((game) => {
                const isItemTracking = trackingGame === (game.slug || game.name);
                return (
                  <PanelSectionRow key={game.slug || game.name}>
                    <ButtonItem
                      layout="below"
                      description={game.slug ? `slug: ${game.slug}` : undefined}
                      onClick={() => handleTrack(game)}
                      disabled={isItemTracking}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }}>
                        <span style={{ fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {game.name}
                        </span>
                        {isItemTracking ? <Spinner /> : <FaPlus style={{ color: "#3498db", flexShrink: 0 }} />}
                      </div>
                    </ButtonItem>
                  </PanelSectionRow>
                );
              })
            )}
          </PanelSection>

          {/* Section 2: Other Steam Games */}
          <PanelSection
            title={`${t.otherSection} (${games.summary.other_count})`}
          >
            {games.other_games.length === 0 ? (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }}>
                  {t.emptyCategory}
                </div>
              </PanelSectionRow>
            ) : (
              games.other_games.map((game) => {
                const isItemTracking = trackingGame === game.name;
                return (
                  <PanelSectionRow key={game.appid || game.name}>
                    <ButtonItem
                      layout="below"
                      description={game.appid ? `AppID: ${game.appid}` : undefined}
                      onClick={() => handleTrack(game)}
                      disabled={isItemTracking}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }}>
                        <span style={{ fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {game.name}
                        </span>
                        {isItemTracking ? <Spinner /> : <FaPlus style={{ color: "#bdc3c7", flexShrink: 0 }} />}
                      </div>
                    </ButtonItem>
                  </PanelSectionRow>
                );
              })
            )}
          </PanelSection>

          {/* Section 3: Tracked Games */}
          <PanelSection
            title={`${t.trackedSection} (${games.summary.tracked_count})`}
          >
            {games.tracked.length === 0 ? (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }}>
                  {t.emptyCategory}
                </div>
              </PanelSectionRow>
            ) : (
              games.tracked.map((game) => (
                <PanelSectionRow key={game.slug || game.name}>
                  <Focusable
                    onActivate={() => {}}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      width: "100%",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      backgroundColor: "rgba(255, 255, 255, 0.04)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                      <FaCheckCircle style={{ color: "#2ecc71", fontSize: "14px", flexShrink: 0 }} />
                      <span
                        style={{
                          fontSize: "13px",
                          fontWeight: "500",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                        }}
                      >
                        {game.name}
                      </span>
                    </div>
                    <Badge color="green">SYNCED</Badge>
                  </Focusable>
                </PanelSectionRow>
              ))
            )}
          </PanelSection>

          {/* Section 4: Missing save folder (collapsed by default) */}
          <PanelSection
            title={`${t.missingFolderSection} (${games.summary.missing_count})`}
          >
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                onClick={() => setShowMissingFolder((prev) => !prev)}
              >
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
                  <PanelSectionRow key={game.slug || game.name}>
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
        </>
      )}
    </>
  );
};

// ==========================================
// Plugin Definition
// ==========================================

export default definePlugin(() => {
  return {
    name: "Hoard Sync",
    icon: <FaCloudUploadAlt />,
    content: <HoardContent />,
    onDismount() {
      // Cleanup hook if needed
    },
  };
});
