import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Upload & Ask',
    description: (
      <>
        Upload PDF, DOCX, Markdown, or plain text documents. Ask questions in
        natural language and get accurate, cited answers grounded in your data.
      </>
    ),
  },
  {
    title: 'Multiple LLM Providers',
    description: (
      <>
        Run locally with Ollama (free), or use OpenAI, Anthropic, or Cloudflare.
        Switch providers from the UI without restarting the server.
      </>
    ),
  },
  {
    title: 'Hybrid Search',
    description: (
      <>
        Combines vector similarity search with BM25 full-text search using
        Reciprocal Rank Fusion for the best of semantic and keyword matching.
      </>
    ),
  },
  {
    title: 'Streaming Citations',
    description: (
      <>
        Real-time SSE streaming with inline Perplexity-style citation markers.
        Click a citation to jump to the source passage with page numbers.
      </>
    ),
  },
  {
    title: 'Plugin System',
    description: (
      <>
        Extensible hook-based plugins: query rewriter, PII redactor,
        cross-encoder re-ranker, and more. Create your own with a simple Python class.
      </>
    ),
  },
  {
    title: 'Self-Hostable',
    description: (
      <>
        Single <code>docker compose up</code> runs everything. No external
        services required. Deploy to Railway or Fly.io for a hosted demo.
      </>
    ),
  },
];

function Feature({title, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md padding-vert--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
