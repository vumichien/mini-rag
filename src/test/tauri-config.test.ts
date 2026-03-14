// @vitest-environment node
/**
 * Phase 06 – Tauri Bundler & Installer validation tests.
 * Verifies that tauri.conf.json, package.json, icon assets, and sidecar binary
 * are correctly configured before running `npm run tauri build`.
 */
import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

// Resolve project root (two levels up from src/test/)
const root = resolve(__dirname, "../..");
const tauriDir = resolve(root, "src-tauri");

// ── helpers ─────────────────────────────────────────────────────────────────

function readJson<T = Record<string, unknown>>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, "utf-8")) as T;
}

function iconPath(name: string) {
  return resolve(tauriDir, "icons", name);
}

// ── tauri.conf.json ──────────────────────────────────────────────────────────

describe("tauri.conf.json – top-level fields", () => {
  const conf = readJson(resolve(tauriDir, "tauri.conf.json"));

  it("productName is 'Mini RAG'", () => {
    expect(conf.productName).toBe("Mini RAG");
  });

  it("identifier is set", () => {
    expect(typeof conf.identifier).toBe("string");
    expect((conf.identifier as string).length).toBeGreaterThan(0);
  });

  it("version is defined", () => {
    expect(typeof conf.version).toBe("string");
  });
});

describe("tauri.conf.json – build section", () => {
  const { build } = readJson<{ build: Record<string, string> }>(
    resolve(tauriDir, "tauri.conf.json"),
  );

  it("devUrl points to localhost:1420", () => {
    expect(build.devUrl).toBe("http://localhost:1420");
  });

  it("frontendDist is '../dist'", () => {
    expect(build.frontendDist).toBe("../dist");
  });
});

describe("tauri.conf.json – app.windows", () => {
  const { app } = readJson<{
    app: { windows: Array<Record<string, unknown>> };
  }>(resolve(tauriDir, "tauri.conf.json"));
  const win = app.windows[0];

  it("title is 'Mini RAG'", () => {
    expect(win.title).toBe("Mini RAG");
  });

  it("width >= 800 and height >= 600", () => {
    expect(win.width as number).toBeGreaterThanOrEqual(800);
    expect(win.height as number).toBeGreaterThanOrEqual(600);
  });

  it("minWidth is 800 and minHeight is 600", () => {
    expect(win.minWidth).toBe(800);
    expect(win.minHeight).toBe(600);
  });

  it("fullscreen is false", () => {
    expect(win.fullscreen).toBe(false);
  });

  it("resizable is true", () => {
    expect(win.resizable).toBe(true);
  });
});

describe("tauri.conf.json – bundle section", () => {
  const { bundle } = readJson<{ bundle: Record<string, unknown> }>(
    resolve(tauriDir, "tauri.conf.json"),
  );

  it("active is true", () => {
    expect(bundle.active).toBe(true);
  });

  it("targets includes 'nsis'", () => {
    expect(bundle.targets).toContain("nsis");
  });

  it("publisher is set", () => {
    expect(typeof bundle.publisher).toBe("string");
    expect((bundle.publisher as string).length).toBeGreaterThan(0);
  });

  it("shortDescription is set", () => {
    expect(typeof bundle.shortDescription).toBe("string");
    expect((bundle.shortDescription as string).length).toBeGreaterThan(0);
  });

  it("icon array contains .ico and .png entries", () => {
    const icons = bundle.icon as string[];
    expect(icons.some((i) => i.endsWith(".ico"))).toBe(true);
    expect(icons.some((i) => i.endsWith(".png"))).toBe(true);
  });

  it("externalBin includes 'binaries/api-server'", () => {
    const bins = bundle.externalBin as string[];
    expect(bins).toContain("binaries/api-server");
  });
});

describe("tauri.conf.json – NSIS installer config", () => {
  type TauriConf = {
    bundle: {
      windows: {
        nsis: {
          shortcutName: string;
          createDesktopShortcut: boolean;
          createStartMenuShortcut: boolean;
          installerIcon: string;
          displayLanguageSelector: boolean;
        };
      };
    };
  };
  const { bundle } = readJson<TauriConf>(resolve(tauriDir, "tauri.conf.json"));
  const nsis = bundle.windows?.nsis;

  it("NSIS config exists", () => {
    expect(nsis).toBeDefined();
  });

  it("shortcutName is 'Mini RAG'", () => {
    expect(nsis.shortcutName).toBe("Mini RAG");
  });

  it("createDesktopShortcut is true", () => {
    expect(nsis.createDesktopShortcut).toBe(true);
  });

  it("createStartMenuShortcut is true", () => {
    expect(nsis.createStartMenuShortcut).toBe(true);
  });

  it("installerIcon points to icons/icon.ico", () => {
    expect(nsis.installerIcon).toBe("icons/icon.ico");
  });

  it("displayLanguageSelector is false", () => {
    expect(nsis.displayLanguageSelector).toBe(false);
  });
});

// ── icon assets ──────────────────────────────────────────────────────────────

describe("Icon assets exist on disk", () => {
  const requiredIcons = [
    "icon.ico",
    "icon.png",
    "32x32.png",
    "128x128.png",
    "128x128@2x.png",
  ];

  for (const name of requiredIcons) {
    it(`icons/${name} exists`, () => {
      expect(existsSync(iconPath(name))).toBe(true);
    });
  }
});

// ── sidecar binary ───────────────────────────────────────────────────────────

describe("Sidecar binary", () => {
  it("api-server-x86_64-pc-windows-msvc.exe exists in src-tauri/binaries/", () => {
    const binaryPath = resolve(tauriDir, "binaries", "api-server-x86_64-pc-windows-msvc.exe");
    expect(existsSync(binaryPath)).toBe(true);
  });
});

// ── package.json scripts ─────────────────────────────────────────────────────

describe("package.json build scripts", () => {
  const pkg = readJson<{ scripts: Record<string, string> }>(resolve(root, "package.json"));

  it("has 'build' script", () => {
    expect(pkg.scripts.build).toBeDefined();
  });

  it("has 'tauri' script", () => {
    expect(pkg.scripts.tauri).toBeDefined();
  });

  it("has 'build:sidecar' script", () => {
    expect(pkg.scripts["build:sidecar"]).toBeDefined();
  });

  it("has 'build:all' script", () => {
    expect(pkg.scripts["build:all"]).toBeDefined();
  });

  it("has 'test' script", () => {
    expect(pkg.scripts.test).toBeDefined();
  });
});
