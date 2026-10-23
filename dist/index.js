const manifest = {"name":"Hoard Sync"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const call = api.call;
const toaster = api.toaster;
const definePlugin = (fn) => {
    return (...args) => {
        return fn(...args);
    };
};

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(e, t) { if (null == e) return {}; var o, r, i = _objectWithoutPropertiesLoose(e, t); if (Object.getOwnPropertySymbols) { var n = Object.getOwnPropertySymbols(e); for (r = 0; r < n.length; r++) o = n[r], -1 === t.indexOf(o) && {}.propertyIsEnumerable.call(e, o) && (i[o] = e[o]); } return i; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (-1 !== e.indexOf(n)) continue; t[n] = r[n]; } return t; }
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: true, configurable: true, writable: true }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var attr = props.attr,
      size = props.size,
      title = props.title,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function FaTimes (props) {
  return GenIcon({"attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M242.72 256l100.07-100.07c12.28-12.28 12.28-32.19 0-44.48l-22.24-22.24c-12.28-12.28-32.19-12.28-44.48 0L176 189.28 75.93 89.21c-12.28-12.28-32.19-12.28-44.48 0L9.21 111.45c-12.28 12.28-12.28 32.19 0 44.48L109.28 256 9.21 356.07c-12.28 12.28-12.28 32.19 0 44.48l22.24 22.24c12.28 12.28 32.2 12.28 44.48 0L176 322.72l100.07 100.07c12.28 12.28 32.2 12.28 44.48 0l22.24-22.24c12.28-12.28 12.28-32.19 0-44.48L242.72 256z"},"child":[]}]})(props);
}function FaSyncAlt (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M370.72 133.28C339.458 104.008 298.888 87.962 255.848 88c-77.458.068-144.328 53.178-162.791 126.85-1.344 5.363-6.122 9.15-11.651 9.15H24.103c-7.498 0-13.194-6.807-11.807-14.176C33.933 94.924 134.813 8 256 8c66.448 0 126.791 26.136 171.315 68.685L463.03 40.97C478.149 25.851 504 36.559 504 57.941V192c0 13.255-10.745 24-24 24H345.941c-21.382 0-32.09-25.851-16.971-40.971l41.75-41.749zM32 296h134.059c21.382 0 32.09 25.851 16.971 40.971l-41.75 41.75c31.262 29.273 71.835 45.319 114.876 45.28 77.418-.07 144.315-53.144 162.787-126.849 1.344-5.363 6.122-9.15 11.651-9.15h57.304c7.498 0 13.194 6.807 11.807 14.176C478.067 417.076 377.187 504 256 504c-66.448 0-126.791-26.136-171.315-68.685L48.97 471.03C33.851 486.149 8 475.441 8 454.059V320c0-13.255 10.745-24 24-24z"},"child":[]}]})(props);
}function FaPlus (props) {
  return GenIcon({"attr":{"viewBox":"0 0 448 512"},"child":[{"tag":"path","attr":{"d":"M416 208H272V64c0-17.67-14.33-32-32-32h-32c-17.67 0-32 14.33-32 32v144H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h144v144c0 17.67 14.33 32 32 32h32c17.67 0 32-14.33 32-32V304h144c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z"},"child":[]}]})(props);
}function FaGamepad (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M480.07 96H160a160 160 0 1 0 114.24 272h91.52A160 160 0 1 0 480.07 96zM248 268a12 12 0 0 1-12 12h-52v52a12 12 0 0 1-12 12h-24a12 12 0 0 1-12-12v-52H84a12 12 0 0 1-12-12v-24a12 12 0 0 1 12-12h52v-52a12 12 0 0 1 12-12h24a12 12 0 0 1 12 12v52h52a12 12 0 0 1 12 12zm216 76a40 40 0 1 1 40-40 40 40 0 0 1-40 40zm64-96a40 40 0 1 1 40-40 40 40 0 0 1-40 40z"},"child":[]}]})(props);
}function FaFolderMinus (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M464 128H272l-64-64H48C21.49 64 0 85.49 0 112v288c0 26.51 21.49 48 48 48h416c26.51 0 48-21.49 48-48V176c0-26.51-21.49-48-48-48zm-96 168c0 8.84-7.16 16-16 16H160c-8.84 0-16-7.16-16-16v-16c0-8.84 7.16-16 16-16h192c8.84 0 16 7.16 16 16v16z"},"child":[]}]})(props);
}function FaExclamationTriangle (props) {
  return GenIcon({"attr":{"viewBox":"0 0 576 512"},"child":[{"tag":"path","attr":{"d":"M569.517 440.013C587.975 472.007 564.806 512 527.94 512H48.054c-36.937 0-59.999-40.055-41.577-71.987L246.423 23.985c18.467-32.009 64.72-31.951 83.154 0l239.94 416.028zM288 354c-25.405 0-46 20.595-46 46s20.595 46 46 46 46-20.595 46-46-20.595-46-46-46zm-43.673-165.346l7.418 136c.347 6.364 5.609 11.346 11.982 11.346h48.546c6.373 0 11.635-4.982 11.982-11.346l7.418-136c.375-6.874-5.098-12.654-11.982-12.654h-63.383c-6.884 0-12.356 5.78-11.981 12.654z"},"child":[]}]})(props);
}function FaDownload (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M216 0h80c13.3 0 24 10.7 24 24v168h87.7c17.8 0 26.7 21.5 14.1 34.1L269.7 378.3c-7.5 7.5-19.8 7.5-27.3 0L90.1 226.1c-12.6-12.6-3.7-34.1 14.1-34.1H192V24c0-13.3 10.7-24 24-24zm296 376v112c0 13.3-10.7 24-24 24H24c-13.3 0-24-10.7-24-24V376c0-13.3 10.7-24 24-24h146.7l49 49c20.1 20.1 52.5 20.1 72.6 0l49-49H488c13.3 0 24 10.7 24 24zm-124 88c0-11-9-20-20-20s-20 9-20 20 9 20 20 20 20-9 20-20zm64 0c0-11-9-20-20-20s-20 9-20 20 9 20 20 20 20-9 20-20z"},"child":[]}]})(props);
}function FaCloudUploadAlt (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M537.6 226.6c4.1-10.7 6.4-22.4 6.4-34.6 0-53-43-96-96-96-19.7 0-38.1 6-53.3 16.2C367 64.2 315.3 32 256 32c-88.4 0-160 71.6-160 160 0 2.7.1 5.4.2 8.1C40.2 219.8 0 273.2 0 336c0 79.5 64.5 144 144 144h368c70.7 0 128-57.3 128-128 0-61.9-44-113.6-102.4-125.4zM393.4 288H328v112c0 8.8-7.2 16-16 16h-48c-8.8 0-16-7.2-16-16V288h-65.4c-14.3 0-21.4-17.2-11.3-27.3l105.4-105.4c6.2-6.2 16.4-6.2 22.6 0l105.4 105.4c10.1 10.1 2.9 27.3-11.3 27.3z"},"child":[]}]})(props);
}function FaChevronRight (props) {
  return GenIcon({"attr":{"viewBox":"0 0 320 512"},"child":[{"tag":"path","attr":{"d":"M285.476 272.971L91.132 467.314c-9.373 9.373-24.569 9.373-33.941 0l-22.667-22.667c-9.357-9.357-9.375-24.522-.04-33.901L188.505 256 34.484 101.255c-9.335-9.379-9.317-24.544.04-33.901l22.667-22.667c9.373-9.373 24.569-9.373 33.941 0L285.475 239.03c9.373 9.372 9.373 24.568.001 33.941z"},"child":[]}]})(props);
}function FaChevronDown (props) {
  return GenIcon({"attr":{"viewBox":"0 0 448 512"},"child":[{"tag":"path","attr":{"d":"M207.029 381.476L12.686 187.132c-9.373-9.373-9.373-24.569 0-33.941l22.667-22.667c9.357-9.357 24.522-9.375 33.901-.04L224 284.505l154.745-154.021c9.379-9.335 24.544-9.317 33.901.04l22.667 22.667c9.373 9.373 9.373 24.569 0 33.941L240.971 381.476c-9.373 9.372-24.569 9.372-33.942 0z"},"child":[]}]})(props);
}function FaCheckCircle (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M504 256c0 136.967-111.033 248-248 248S8 392.967 8 256 119.033 8 256 8s248 111.033 248 248zM227.314 387.314l184-184c6.248-6.248 6.248-16.379 0-22.627l-22.627-22.627c-6.248-6.249-16.379-6.249-22.628 0L216 308.118l-70.059-70.059c-6.248-6.248-16.379-6.248-22.628 0l-22.627 22.627c-6.248 6.248-6.248 16.379 0 22.627l104 104c6.249 6.249 16.379 6.249 22.628.001z"},"child":[]}]})(props);
}

// ==========================================
// i18n Localization
// ==========================================
const getLanguage = () => {
    try {
        const steamLang = window.SteamClient?.Settings?.GetCurrentLanguage?.()?.toLowerCase();
        if (steamLang === "french" || steamLang === "fr")
            return "fr";
    }
    catch { }
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
const Badge = ({ children, color = "blue", }) => {
    const styles = {
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
    return (SP_JSX.jsx("span", { style: {
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
        }, children: children }));
};
// ==========================================
// Main Plugin Content Component
// ==========================================
const HoardContent = () => {
    const lang = SP_REACT.useMemo(() => getLanguage(), []);
    const t = STRINGS[lang];
    const [status, setStatus] = SP_REACT.useState(null);
    const [games, setGames] = SP_REACT.useState(null);
    const [isLoadingStatus, setIsLoadingStatus] = SP_REACT.useState(true);
    const [isLoadingGames, setIsLoadingGames] = SP_REACT.useState(false);
    const [isInstalling, setIsInstalling] = SP_REACT.useState(false);
    const [isSyncing, setIsSyncing] = SP_REACT.useState(false);
    const [busyGame, setBusyGame] = SP_REACT.useState(null);
    const [showMissingFolder, setShowMissingFolder] = SP_REACT.useState(false);
    const fetchStatus = SP_REACT.useCallback(async () => {
        try {
            setIsLoadingStatus(true);
            const res = await call("get_status");
            setStatus(res);
            return res;
        }
        catch (e) {
            console.error("Failed to get Hoard status", e);
            return null;
        }
        finally {
            setIsLoadingStatus(false);
        }
    }, []);
    const fetchGames = SP_REACT.useCallback(async (forceRefresh = false) => {
        try {
            setIsLoadingGames(true);
            const res = await call("get_games", forceRefresh);
            setGames(res);
        }
        catch (e) {
            console.error("Failed to load games list", e);
        }
        finally {
            setIsLoadingGames(false);
        }
    }, []);
    SP_REACT.useEffect(() => {
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
            const res = await call("install_hoard");
            if (res.ok) {
                toaster.toast({ title: t.pluginTitle, body: t.installSuccess, duration: 3000 });
                await fetchStatus();
                fetchGames(true);
            }
            else {
                toaster.toast({ title: t.pluginTitle, body: `${t.installFailed}${res.message}`, duration: 5000 });
            }
        }
        catch (err) {
            toaster.toast({ title: t.pluginTitle, body: `${t.installFailed}${err?.message || err}`, duration: 5000 });
        }
        finally {
            setIsInstalling(false);
        }
    };
    const handleSyncNow = async () => {
        setIsSyncing(true);
        toaster.toast({ title: t.pluginTitle, body: t.syncing, duration: 3000 });
        try {
            const res = await call("force_sync");
            if (res.ok) {
                toaster.toast({ title: t.pluginTitle, body: res.message || t.syncSuccess, duration: 3000 });
                fetchStatus();
                fetchGames(true);
            }
            else {
                toaster.toast({ title: t.pluginTitle, body: `${t.syncFailed}${res.message}`, duration: 5000 });
            }
        }
        catch (err) {
            toaster.toast({ title: t.pluginTitle, body: `${t.syncFailed}${err?.message || err}`, duration: 5000 });
        }
        finally {
            setIsSyncing(false);
        }
    };
    const handleTrack = async (game) => {
        setBusyGame(game.slug);
        try {
            const res = await call("track_game", game.name, game.slug);
            if (res.ok) {
                toaster.toast({ title: t.pluginTitle, body: `"${game.name}" ${t.trackSuccess}`, duration: 3000 });
                fetchGames(true);
            }
            else {
                toaster.toast({ title: t.pluginTitle, body: `${t.trackFailed}${res.message}`, duration: 5000 });
            }
        }
        catch (err) {
            toaster.toast({ title: t.pluginTitle, body: `${t.trackFailed}${err?.message || err}`, duration: 5000 });
        }
        finally {
            setBusyGame(null);
        }
    };
    const handleUntrack = async (game) => {
        if (!game.save_id)
            return;
        setBusyGame(game.slug);
        try {
            const res = await call("untrack_game", game.save_id);
            if (res.ok) {
                toaster.toast({ title: t.pluginTitle, body: `"${game.name}" ${t.untrackSuccess}`, duration: 3000 });
                fetchGames(true);
            }
            else {
                toaster.toast({ title: t.pluginTitle, body: `${t.untrackFailed}${res.message}`, duration: 5000 });
            }
        }
        catch (err) {
            toaster.toast({ title: t.pluginTitle, body: `${t.untrackFailed}${err?.message || err}`, duration: 5000 });
        }
        finally {
            setBusyGame(null);
        }
    };
    if (isLoadingStatus && !status) {
        return (SP_JSX.jsx(DFL.PanelSection, { children: SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { display: "flex", justifyContent: "center", padding: "24px" }, children: SP_JSX.jsx(DFL.Spinner, {}) }) }) }));
    }
    if (!status?.installed) {
        return (SP_JSX.jsxs(DFL.PanelSection, { title: t.notInstalledTitle, children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                            padding: "12px",
                            backgroundColor: "rgba(231, 76, 60, 0.12)",
                            borderRadius: "8px",
                            border: "1px solid rgba(231, 76, 60, 0.3)",
                            marginBottom: "12px",
                            display: "flex",
                            alignItems: "flex-start",
                            gap: "10px",
                        }, children: [SP_JSX.jsx(FaExclamationTriangle, { style: { color: "#e74c3c", fontSize: "20px", marginTop: "2px", flexShrink: 0 } }), SP_JSX.jsx("div", { style: { fontSize: "13px", lineHeight: "1.4" }, children: t.notInstalledDesc })] }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: handleInstall, disabled: isInstalling, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }, children: [isInstalling ? SP_JSX.jsx(DFL.Spinner, {}) : SP_JSX.jsx(FaDownload, {}), SP_JSX.jsx("span", { children: isInstalling ? t.installing : t.installBtn })] }) }) })] }));
    }
    const accountLabel = status.user_info?.email ||
        (status.user_info?.username ? `${status.user_info.username}` : null);
    return (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: t.syncSection, children: [!status.logged_in && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                                padding: "10px",
                                backgroundColor: "rgba(241, 196, 15, 0.12)",
                                borderRadius: "8px",
                                border: "1px solid rgba(241, 196, 15, 0.35)",
                                marginBottom: "10px",
                                display: "flex",
                                alignItems: "flex-start",
                                gap: "10px",
                            }, children: [SP_JSX.jsx(FaExclamationTriangle, { style: { color: "#f1c40f", fontSize: "18px", marginTop: "2px", flexShrink: 0 } }), SP_JSX.jsxs("div", { style: { fontSize: "12px", lineHeight: "1.4" }, children: [SP_JSX.jsxs("strong", { children: [t.sessionRequiredTitle, ":"] }), " ", t.sessionRequiredDesc] })] }) })), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                width: "100%",
                                padding: "4px 0",
                                fontSize: "13px",
                            }, children: [SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column" }, children: [SP_JSX.jsx("span", { children: status.service_running ? t.daemonActive : t.daemonInactive }), accountLabel && (SP_JSX.jsx("span", { style: { fontSize: "11px", color: "#888" }, children: accountLabel }))] }), SP_JSX.jsx(Badge, { color: status.service_running ? "green" : "gray", children: status.service_running ? "ONLINE" : "OFFLINE" })] }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: handleSyncNow, disabled: isSyncing, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }, children: [isSyncing ? SP_JSX.jsx(DFL.Spinner, {}) : SP_JSX.jsx(FaSyncAlt, {}), SP_JSX.jsx("span", { children: isSyncing ? t.syncing : t.syncNow })] }) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => fetchGames(true), disabled: isLoadingGames, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }, children: [isLoadingGames ? SP_JSX.jsx(DFL.Spinner, {}) : SP_JSX.jsx(FaGamepad, {}), SP_JSX.jsx("span", { children: isLoadingGames ? t.scanning : t.refreshBtn })] }) }) })] }), isLoadingGames && !games && (SP_JSX.jsx(DFL.PanelSection, { children: SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { display: "flex", justifyContent: "center", padding: "16px" }, children: SP_JSX.jsx(DFL.Spinner, {}) }) }) })), games && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSection, { title: `${t.trackedSection} (${games.summary.tracked_count})`, children: games.tracked.length === 0 ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }, children: t.emptyCategory }) })) : (games.tracked.map((game) => {
                            const isBusy = busyGame === game.slug;
                            const verLabel = game.last_version_num ? `v${game.last_version_num}` : "SYNCED";
                            return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", description: game.slug, onClick: () => handleUntrack(game), disabled: isBusy || !game.save_id, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }, children: [SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }, children: [SP_JSX.jsx(FaCheckCircle, { style: { color: "#2ecc71", fontSize: "13px", flexShrink: 0 } }), SP_JSX.jsx("span", { style: { fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: game.name })] }), SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }, children: [SP_JSX.jsx(Badge, { color: game.paused ? "amber" : "green", children: game.paused ? "PAUSED" : verLabel }), isBusy ? SP_JSX.jsx(DFL.Spinner, {}) : game.save_id ? SP_JSX.jsx(FaTimes, { style: { color: "#888", fontSize: "11px" } }) : null] })] }) }) }, game.slug));
                        })) }), SP_JSX.jsx(DFL.PanelSection, { title: `${t.readySection} (${games.summary.ready_count})`, children: games.ready_to_track.length === 0 ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", color: "#888", fontStyle: "italic", padding: "4px 0" }, children: t.emptyCategory }) })) : (games.ready_to_track.map((game) => {
                            const isBusy = busyGame === game.slug;
                            return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", description: game.slug, onClick: () => handleTrack(game), disabled: isBusy, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", gap: "8px" }, children: [SP_JSX.jsx("span", { style: { fontSize: "13px", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis" }, children: game.name }), isBusy ? SP_JSX.jsx(DFL.Spinner, {}) : SP_JSX.jsx(FaPlus, { style: { color: "#3498db", flexShrink: 0 } })] }) }) }, game.slug));
                        })) }), games.summary.missing_count > 0 && (SP_JSX.jsxs(DFL.PanelSection, { title: `${t.missingFolderSection} (${games.summary.missing_count})`, children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => setShowMissingFolder((prev) => !prev), children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }, children: [showMissingFolder ? SP_JSX.jsx(FaChevronDown, {}) : SP_JSX.jsx(FaChevronRight, {}), SP_JSX.jsxs("span", { children: [showMissingFolder ? t.collapse : t.expand, " (", games.summary.missing_count, ")"] })] }) }) }), showMissingFolder && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#888", marginBottom: "6px" }, children: t.missingFolderDesc }) }), games.missing_folder.map((game) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.Focusable, { onActivate: () => { }, style: {
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "8px",
                                                width: "100%",
                                                padding: "6px 8px",
                                                borderRadius: "4px",
                                                opacity: 0.6,
                                                backgroundColor: "rgba(0, 0, 0, 0.15)",
                                            }, children: [SP_JSX.jsx(FaFolderMinus, { style: { color: "#f39c12", fontSize: "14px", flexShrink: 0 } }), SP_JSX.jsx("span", { style: {
                                                        fontSize: "12px",
                                                        textOverflow: "ellipsis",
                                                        whiteSpace: "nowrap",
                                                        overflow: "hidden",
                                                    }, children: game.name })] }) }, game.slug)))] }))] }))] }))] }));
};
var index = definePlugin(() => {
    return {
        name: "Hoard Sync",
        icon: SP_JSX.jsx(FaCloudUploadAlt, {}),
        content: SP_JSX.jsx(HoardContent, {}),
        onDismount() { },
    };
});

export { index as default };
//# sourceMappingURL=index.js.map
