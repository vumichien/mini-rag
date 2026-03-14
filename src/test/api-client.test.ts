import { describe, it, expect, vi, beforeEach } from "vitest";
import { checkHealth, uploadPDF, getDocuments, deleteDocument, search } from "../lib/api-client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function makeFetchOk(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

describe("checkHealth", () => {
  beforeEach(() => mockFetch.mockReset());

  it("returns true when /health responds 200", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true } as Response);
    expect(await checkHealth()).toBe(true);
  });

  it("returns false when fetch throws", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network error"));
    expect(await checkHealth()).toBe(false);
  });

  it("returns false when status is not ok", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false } as Response);
    expect(await checkHealth()).toBe(false);
  });
});

describe("uploadPDF", () => {
  beforeEach(() => mockFetch.mockReset());

  it("returns upload response on success", async () => {
    const responseBody = { doc_id: "abc123", filename: "test.pdf", chunk_count: 5 };
    mockFetch.mockResolvedValueOnce(makeFetchOk(responseBody));
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    const result = await uploadPDF(file);
    expect(result).toEqual(responseBody);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://127.0.0.1:52547/upload",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve("Bad Request"),
    } as Response);
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    await expect(uploadPDF(file)).rejects.toThrow("Bad Request");
  });
});

describe("getDocuments", () => {
  beforeEach(() => mockFetch.mockReset());

  it("returns list of documents", async () => {
    const docs = [{ doc_id: "1", filename: "a.pdf", chunk_count: 3 }];
    mockFetch.mockResolvedValueOnce(makeFetchOk({ documents: docs }));
    const result = await getDocuments();
    expect(result).toEqual(docs);
    expect(mockFetch).toHaveBeenCalledWith("http://127.0.0.1:52547/documents");
  });

  it("returns empty array when no documents", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchOk({ documents: [] }));
    const result = await getDocuments();
    expect(result).toEqual([]);
  });
});

describe("deleteDocument", () => {
  beforeEach(() => mockFetch.mockReset());

  it("calls DELETE on the correct endpoint", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true } as Response);
    await deleteDocument("doc-abc");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://127.0.0.1:52547/documents/doc-abc",
      { method: "DELETE" },
    );
  });
});

describe("search", () => {
  beforeEach(() => mockFetch.mockReset());

  it("returns search results", async () => {
    const results = [
      { text: "hello world", filename: "a.pdf", page_number: 1, chunk_index: 0, score: 0.95 },
    ];
    mockFetch.mockResolvedValueOnce(makeFetchOk({ results }));
    const result = await search("hello");
    expect(result).toEqual(results);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://127.0.0.1:52547/search",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "hello", n_results: 5 }),
      }),
    );
  });

  it("returns empty results array", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchOk({ results: [] }));
    const result = await search("nothing");
    expect(result).toEqual([]);
  });
});
