"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./page.module.css";

type DocumentTreeTopic = {
  doc_id: string;
  title: string;
  vendor: string | null;
  release: string | null;
  node_type: string | null;
};

type DocumentTreeDomain = {
  name: string;
  topics: DocumentTreeTopic[];
};

type DocumentTreeRelease = {
  name: string;
  domains: DocumentTreeDomain[];
};

type DocumentTreeProduct = {
  name: string;
  releases: DocumentTreeRelease[];
};

type DocumentTreeResponse = {
  products: DocumentTreeProduct[];
};

type DocumentChunkRecord = {
  chunk_id: string;
  content: string;
};

type DocumentRecord = {
  doc_id: string;
  title: string;
  chunk_count: number;
  source_format: string;
  chunks: DocumentChunkRecord[];
};

type DocSelection = {
  product: string;
  release: string;
  domain: string;
  docId: string;
};

type SectionAnchor = {
  id: string;
  label: string;
};

type SavedSearch = {
  id: string;
  query: string;
};

type PinnedSection = {
  docId: string;
  anchorId: string;
  label: string;
};

const SAVED_SEARCHES_KEY = "library.client.saved-searches";
const PINNED_SECTIONS_KEY = "library.client.pinned-sections";

function loadSavedSearches(): SavedSearch[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(SAVED_SEARCHES_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as SavedSearch[];
    return parsed.filter((item) => item?.query?.trim());
  } catch {
    return [];
  }
}

function loadPinnedSections(): PinnedSection[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(PINNED_SECTIONS_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as PinnedSection[];
    return parsed.filter((item) => item?.docId && item?.anchorId);
  } catch {
    return [];
  }
}

function makeSectionLabel(content: string, index: number): string {
  const firstLine = content
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.length > 0);

  if (!firstLine) {
    return `Раздел ${index + 1}`;
  }

  return firstLine.length > 60 ? `${firstLine.slice(0, 57)}...` : firstLine;
}

function pickInitialSelection(tree: DocumentTreeResponse): DocSelection | null {
  const firstProduct = tree.products[0];
  const firstRelease = firstProduct?.releases[0];
  const firstDomain = firstRelease?.domains[0];
  const firstTopic = firstDomain?.topics[0];

  if (!firstProduct || !firstRelease || !firstDomain || !firstTopic) {
    return null;
  }

  return {
    product: firstProduct.name,
    release: firstRelease.name,
    domain: firstDomain.name,
    docId: firstTopic.doc_id,
  };
}

function findTopicByDocId(tree: DocumentTreeResponse, docId: string): DocSelection | null {
  for (const product of tree.products) {
    for (const release of product.releases) {
      for (const domain of release.domains) {
        const topic = domain.topics.find((item) => item.doc_id === docId);
        if (topic) {
          return {
            product: product.name,
            release: release.name,
            domain: domain.name,
            docId,
          };
        }
      }
    }
  }
  return null;
}

export default function Home() {
  const [tree, setTree] = useState<DocumentTreeResponse | null>(null);
  const [selection, setSelection] = useState<DocSelection | null>(null);
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [error, setError] = useState<string>("");
  const [treeFilter, setTreeFilter] = useState("");
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(loadSavedSearches);
  const [pinnedSections, setPinnedSections] = useState<PinnedSection[]>(loadPinnedSections);

  useEffect(() => {
    window.localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(savedSearches));
  }, [savedSearches]);

  useEffect(() => {
    window.localStorage.setItem(PINNED_SECTIONS_KEY, JSON.stringify(pinnedSections));
  }, [pinnedSections]);

  useEffect(() => {
    const loadTree = async () => {
      setLoadingTree(true);
      setError("");
      try {
        const response = await fetch("/api/documents/tree", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Tree request failed: ${response.status}`);
        }
        const payload: DocumentTreeResponse = await response.json();
        setTree(payload);

        const initialSelection = pickInitialSelection(payload);
        if (initialSelection) {
          setSelection(initialSelection);
        }
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Tree request failed");
      } finally {
        setLoadingTree(false);
      }
    };

    void loadTree();
  }, []);

  useEffect(() => {
    const loadDocument = async () => {
      if (!selection?.docId) {
        return;
      }

      setLoadingDocument(true);
      setError("");
      try {
        const response = await fetch(`/api/documents/${encodeURIComponent(selection.docId)}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Document request failed: ${response.status}`);
        }
        const payload: DocumentRecord = await response.json();
        setDocument(payload);
      } catch (requestError) {
        setDocument(null);
        setError(requestError instanceof Error ? requestError.message : "Document request failed");
      } finally {
        setLoadingDocument(false);
      }
    };

    void loadDocument();
  }, [selection?.docId]);

  const activeProduct = useMemo(
    () => tree?.products.find((product) => product.name === selection?.product) ?? null,
    [tree, selection?.product],
  );

  const releaseOptions = useMemo(
    () => activeProduct?.releases.map((release) => release.name) ?? [],
    [activeProduct],
  );

  const normalizedFilter = treeFilter.trim().toLowerCase();

  const filteredTree = useMemo<DocumentTreeResponse>(() => {
    if (!tree) {
      return { products: [] };
    }

    if (!normalizedFilter) {
      return tree;
    }

    return {
      products: tree.products
        .map((product) => ({
          ...product,
          releases: product.releases
            .map((release) => ({
              ...release,
              domains: release.domains
                .map((domain) => ({
                  ...domain,
                  topics: domain.topics.filter((topic) => {
                    const haystack = [product.name, release.name, domain.name, topic.title]
                      .join(" ")
                      .toLowerCase();
                    return haystack.includes(normalizedFilter);
                  }),
                }))
                .filter((domain) => domain.topics.length > 0),
            }))
            .filter((release) => release.domains.length > 0),
        }))
        .filter((product) => product.releases.length > 0),
    };
  }, [normalizedFilter, tree]);

  const breadcrumbs = useMemo(() => {
    if (!selection || !document) {
      return [] as string[];
    }
    return [selection.product, selection.release, selection.domain, document.title];
  }, [selection, document]);

  const sectionAnchors = useMemo<SectionAnchor[]>(() => {
    if (!document) {
      return [];
    }
    return document.chunks.map((chunk, index) => ({
      id: `section-${index + 1}`,
      label: makeSectionLabel(chunk.content, index),
    }));
  }, [document]);

  const pinnedForCurrentDoc = useMemo(
    () => pinnedSections.filter((item) => item.docId === document?.doc_id),
    [document?.doc_id, pinnedSections],
  );

  const saveCurrentSearch = () => {
    const query = treeFilter.trim();
    if (!query) {
      return;
    }

    setSavedSearches((previous) => {
      if (previous.some((item) => item.query.toLowerCase() === query.toLowerCase())) {
        return previous;
      }
      return [{ id: `${Date.now()}`, query }, ...previous].slice(0, 8);
    });
  };

  const deleteSavedSearch = (id: string) => {
    setSavedSearches((previous) => previous.filter((item) => item.id !== id));
  };

  const togglePinnedSection = (anchor: SectionAnchor) => {
    if (!document) {
      return;
    }

    setPinnedSections((previous) => {
      const exists = previous.some(
        (item) => item.docId === document.doc_id && item.anchorId === anchor.id,
      );

      if (exists) {
        return previous.filter(
          (item) => !(item.docId === document.doc_id && item.anchorId === anchor.id),
        );
      }

      return [
        {
          docId: document.doc_id,
          anchorId: anchor.id,
          label: anchor.label,
        },
        ...previous,
      ];
    });
  };

  const handleVersionChange = (releaseName: string) => {
    if (!tree || !selection) {
      return;
    }

    const product = tree.products.find((item) => item.name === selection.product);
    const release = product?.releases.find((item) => item.name === releaseName);
    const domain = release?.domains[0];
    const topic = domain?.topics[0];
    if (!product || !release || !domain || !topic) {
      return;
    }

    setSelection({
      product: product.name,
      release: release.name,
      domain: domain.name,
      docId: topic.doc_id,
    });
  };

  const handleTopicSelect = (docId: string) => {
    if (!tree) {
      return;
    }

    const resolvedSelection = findTopicByDocId(tree, docId);
    if (resolvedSelection) {
      setSelection(resolvedSelection);
    }
  };

  if (loadingTree) {
    return <div className={styles.centered}>Загрузка дерева документации...</div>;
  }

  if (!tree || tree.products.length === 0) {
    return <div className={styles.centered}>Дерево документации пусто</div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <h1>Library Client</h1>
        <div className={styles.versionBlock}>
          <label htmlFor="version-select">Версия релиза</label>
          <select
            id="version-select"
            value={selection?.release ?? ""}
            onChange={(event) => handleVersionChange(event.target.value)}
          >
            {releaseOptions.map((releaseName) => (
              <option key={releaseName} value={releaseName}>
                {releaseName}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <h2>Дерево документации</h2>
          <div className={styles.sidebarTools}>
            <input
              value={treeFilter}
              onChange={(event) => setTreeFilter(event.target.value)}
              placeholder="Фильтр по дереву"
              className={styles.filterInput}
            />
            <div className={styles.searchActions}>
              <button type="button" className={styles.secondaryButton} onClick={saveCurrentSearch}>
                Сохранить поиск
              </button>
              <button type="button" className={styles.secondaryButton} onClick={() => setTreeFilter("")}>
                Очистить
              </button>
            </div>

            {savedSearches.length > 0 ? (
              <ul className={styles.savedSearchList}>
                {savedSearches.map((item) => (
                  <li key={item.id} className={styles.savedSearchItem}>
                    <button
                      type="button"
                      className={styles.chipButton}
                      onClick={() => setTreeFilter(item.query)}
                    >
                      {item.query}
                    </button>
                    <button
                      type="button"
                      className={styles.iconButton}
                      onClick={() => deleteSavedSearch(item.id)}
                      aria-label="Удалить сохраненный поиск"
                    >
                      x
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <div className={styles.tree}>
            {filteredTree.products.map((product) => (
              <details
                key={product.name}
                open={product.name === selection?.product}
                className={styles.treeProduct}
              >
                <summary>{product.name}</summary>
                {product.releases.map((release) => (
                  <details
                    key={`${product.name}-${release.name}`}
                    open={product.name === selection?.product && release.name === selection?.release}
                    className={styles.treeRelease}
                  >
                    <summary>{release.name}</summary>
                    {release.domains.map((domain) => (
                      <div key={`${release.name}-${domain.name}`} className={styles.treeDomain}>
                        <h4>{domain.name}</h4>
                        <ul>
                          {domain.topics.map((topic) => (
                            <li key={topic.doc_id}>
                              <button
                                type="button"
                                onClick={() => handleTopicSelect(topic.doc_id)}
                                className={
                                  topic.doc_id === selection?.docId ? styles.topicActive : styles.topicButton
                                }
                              >
                                {topic.title}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </details>
                ))}
              </details>
            ))}
            {filteredTree.products.length === 0 ? (
              <p className={styles.meta}>По текущему фильтру ничего не найдено.</p>
            ) : null}
          </div>
        </aside>

        <main className={styles.content}>
          <nav className={styles.breadcrumbs} aria-label="breadcrumbs">
            {breadcrumbs.length > 0 ? breadcrumbs.join(" / ") : "Выберите документ"}
          </nav>

          {error ? <p className={styles.error}>{error}</p> : null}
          {loadingDocument ? <p className={styles.meta}>Загрузка документа...</p> : null}

          {document ? (
            <article className={styles.article}>
              <header className={styles.articleHeader}>
                <h2>{document.title}</h2>
                <p className={styles.meta}>
                  doc_id: {document.doc_id} | source: {document.source_format} | chunks: {document.chunk_count}
                </p>
              </header>

              <section className={styles.anchors}>
                <h3>Якоря разделов</h3>
                {pinnedForCurrentDoc.length > 0 ? (
                  <div className={styles.pinnedBlock}>
                    <h4>Закрепленные</h4>
                    <ul>
                      {pinnedForCurrentDoc.map((pin) => (
                        <li key={`${pin.docId}-${pin.anchorId}`}>
                          <a href={`#${pin.anchorId}`}>{pin.label}</a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <ul>
                  {sectionAnchors.map((anchor) => (
                    <li key={anchor.id}>
                      <a href={`#${anchor.id}`}>{anchor.label}</a>
                      <button
                        type="button"
                        className={styles.iconButton}
                        onClick={() => togglePinnedSection(anchor)}
                        aria-label="Закрепить раздел"
                      >
                        {pinnedForCurrentDoc.some((pin) => pin.anchorId === anchor.id) ? "-" : "+"}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className={styles.documentBody}>
                {document.chunks.map((chunk, index) => {
                  const anchor = sectionAnchors[index];
                  return (
                    <section key={chunk.chunk_id} id={anchor?.id} className={styles.chunk}>
                      <h4>{anchor?.label ?? `Раздел ${index + 1}`}</h4>
                      <pre>{chunk.content}</pre>
                    </section>
                  );
                })}
              </section>
            </article>
          ) : (
            <p className={styles.meta}>Документ не выбран.</p>
          )}
        </main>
      </div>
    </div>
  );
}
