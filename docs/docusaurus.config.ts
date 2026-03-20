import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'doc-qna',
  tagline: 'Upload documents, ask questions, get answers with sources',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://elvisbui.github.io',
  baseUrl: '/doc-qna/',

  organizationName: 'elvisbui',
  projectName: 'doc-qna',

  onBrokenLinks: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/elvisbui/doc-qna/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        indexBlog: false,
      },
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    metadata: [
      {name: 'keywords', content: 'RAG, document QA, retrieval augmented generation, LLM, vector search, ChromaDB, FastAPI'},
      {name: 'twitter:card', content: 'summary_large_image'},
    ],
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'doc-qna',
      hideOnScroll: true,
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          type: 'search',
          position: 'right',
        },
        {
          href: 'https://github.com/elvisbui/doc-qna',
          'aria-label': 'GitHub repository',
          position: 'right',
          className: 'header-github-link',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {label: 'Getting Started', to: '/docs/getting-started/installation'},
            {label: 'Architecture', to: '/docs/architecture/overview'},
            {label: 'API Reference', to: '/docs/api/endpoints'},
          ],
        },
        {
          title: 'Guides',
          items: [
            {label: 'Configuration', to: '/docs/configuration/environment-variables'},
            {label: 'Plugins', to: '/docs/plugins/overview'},
            {label: 'Deployment', to: '/docs/deployment/docker'},
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/elvisbui/doc-qna',
            },
            {
              label: 'Report an Issue',
              href: 'https://github.com/elvisbui/doc-qna/issues',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} doc-qna. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python', 'docker', 'yaml', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
