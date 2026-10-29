{
  lib,
  stdenv,
  fetchurl,
  buildFHSEnv,
  desktop-file-utils,
  imagemagick,
  alsa-lib,
  at-spi2-atk,
  at-spi2-core,
  atk,
  cairo,
  cups,
  curl,
  dbus,
  expat,
  fontconfig,
  freetype,
  gdk-pixbuf,
  glib,
  glibc,
  gtk3,
  icu,
  libdrm,
  libgbm,
  libglvnd,
  libnotify,
  libpulseaudio,
  libsecret,
  libudev0-shim,
  libunwind,
  libuuid,
  libxkbcommon,
  libxkbfile,
  lttng-ust,
  mesa,
  nspr,
  nss,
  openssl,
  pango,
  systemd,
  udev,
  zlib,
  libX11,
  libXScrnSaver,
  libXcomposite,
  libXcursor,
  libXdamage,
  libXext,
  libXfixes,
  libXi,
  libXrandr,
  libXrender,
  libXtst,
  libxcb,
  libxshmfence,
}:

let
  pname = "antigravity-hub";
  version = "2.28.1";

  antigravity-hub-unwrapped = stdenv.mkDerivation {
    pname = "${pname}-unwrapped";
    inherit version;

    src = fetchurl {
      name = "Antigravity-Hub-${version}-linux-x64.tar.gz";
      url = "https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/linux-x64/Antigravity.tar.gz";
      hash = "sha256-FbFVeOQy6kMuf8kKxi4UCoRO6ylWU69yql/Vo2SU3vc=";
    };

    # The tarball unpacks into Antigravity-x64/
    sourceRoot = "Antigravity-x64";

    nativeBuildInputs = [
      desktop-file-utils
      imagemagick
    ];

    # autoPatchelf is NOT used here; FHSEnv handles library resolution.
    # The Hub binary is a pre-linked Electron executable that locates all
    # shared libraries through the FHS LD path at runtime.
    dontAutoPatchelf = true;
    dontFixup = true;

    installPhase = ''
      runHook preInstall

      mkdir -p $out/opt/antigravity-hub
      mkdir -p $out/share/applications
      mkdir -p $out/share/pixmaps
      mkdir -p $out/share/icons/hicolor/scalable/apps

      # Install the application itself
      cp -r . $out/opt/antigravity-hub/

      # Install scaled icons from the bundled icon if present, else from assets
      if [ -f resources/app/assets/AntigravityLogo.png ]; then
        _icon_src=resources/app/assets/AntigravityLogo.png
      elif [ -f resources/app.asar.unpacked/assets/AntigravityLogo.png ]; then
        _icon_src=resources/app.asar.unpacked/assets/AntigravityLogo.png
      else
        _icon_src=${./assets/antigravity-hub.png}
      fi

      for size in 16 24 32 48 64 128 256 512 1024; do
        mkdir -p $out/share/icons/hicolor/''${size}x''${size}/apps
        magick "$_icon_src" -filter Lanczos -resize ''${size}x''${size} \
          $out/share/icons/hicolor/''${size}x''${size}/apps/antigravity-hub.png
        ln -s antigravity-hub.png $out/share/icons/hicolor/''${size}x''${size}/apps/antigravity.png
      done
      install -Dm644 ${./assets/antigravity-hub.png} $out/share/pixmaps/antigravity-hub.png
      ln -s antigravity-hub.png $out/share/pixmaps/antigravity.png

      # Install desktop entries (both canonical antigravity-hub and Wayland app_id alias antigravity)
      install -Dm644 ${./assets/antigravity-hub.desktop} \
        $out/share/applications/antigravity-hub.desktop
      ln -s antigravity-hub.desktop $out/share/applications/antigravity.desktop

      # Validate the desktop files
      desktop-file-validate $out/share/applications/antigravity-hub.desktop
      desktop-file-validate $out/share/applications/antigravity.desktop

      runHook postInstall
    '';
  };

  meta = with lib; {
    description = "Google Antigravity 2.0 — agentic AI coding command center and mission control";
    homepage = "https://antigravity.google";
    downloadPage = "https://antigravity.google/download";
    changelog = "https://antigravity.google/changelog";
    license = licenses.unfree;
    sourceProvenance = [ sourceTypes.binaryNativeCode ];
    platforms = [ "x86_64-linux" ];
    mainProgram = pname;
    priority = 10;
  };

in
buildFHSEnv {
  name = pname;
  inherit version meta;

  targetPkgs = pkgs: [
    antigravity-hub-unwrapped
    # System base
    pkgs.glibc
    pkgs.zlib
    # Graphics / EGL / GPU
    alsa-lib
    at-spi2-atk
    at-spi2-core
    atk
    cairo
    cups
    curl
    dbus
    expat
    fontconfig
    freetype
    gdk-pixbuf
    glib
    gtk3
    icu
    libdrm
    libgbm
    libglvnd
    libnotify
    libpulseaudio
    libsecret
    libudev0-shim
    libunwind
    libuuid
    libxkbcommon
    libxkbfile
    lttng-ust
    mesa
    nspr
    nss
    openssl
    pango
    systemd
    udev
    # X11
    libX11
    libXScrnSaver
    libXcomposite
    libXcursor
    libXdamage
    libXext
    libXfixes
    libXi
    libXrandr
    libXrender
    libXtst
    libxcb
    libxshmfence
  ];

  extraBwrapArgs = [
    # Allow the Hub to read the NixOS config and XDG data for integrations.
    "--bind-try /etc/nixos/ /etc/nixos/"
    "--ro-bind-try /etc/xdg/ /etc/xdg/"
  ];

  runScript = "${antigravity-hub-unwrapped}/opt/antigravity-hub/antigravity";

  extraInstallCommands = ''
    mkdir -p $out/share/applications $out/share/pixmaps $out/share/icons
    ln -s ${antigravity-hub-unwrapped}/share/applications/* $out/share/applications/
    ln -s ${antigravity-hub-unwrapped}/share/pixmaps/* $out/share/pixmaps/
    cp -r ${antigravity-hub-unwrapped}/share/icons/* $out/share/icons/
  '';

  passthru = {
    unwrapped = antigravity-hub-unwrapped;
    inherit version;
  };
}
