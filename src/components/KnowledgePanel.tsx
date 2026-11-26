import React, { useState } from 'react';
import { 
  BookOpen, 
  ChevronRight, 
  ChevronDown, 
  FileText, 
  Zap, 
  ExternalLink, 
  ShieldCheck, 
  CheckCircle, 
  Bookmark, 
  Plus, 
  Sparkles,
  Search,
  SlidersHorizontal
} from 'lucide-react';
import { KnowledgeArticle, CannedMacro, CustomerProfile } from '../types';

interface KnowledgePanelProps {
  articles: KnowledgeArticle[];
  macros: CannedMacro[];
  customerProfile: CustomerProfile;
  onInsertText: (text: string) => void;
}

export const KnowledgePanel: React.FC<KnowledgePanelProps> = ({
  articles,
  macros,
  customerProfile,
  onInsertText
}) => {
  const [expandedArticleId, setExpandedArticleId] = useState<string | null>(articles[0]?.id || null);
  const [activeTab, setActiveTab] = useState<'articles' | 'macros' | 'account'>('articles');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredArticles = articles.filter(a => 
    a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredMacros = macros.filter(m =>
    m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.shortcut.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-slate-900/95 border-l border-slate-800">
      {/* 1. Header & Tabs */}
      <div className="p-3.5 bg-slate-900 border-b border-slate-800 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <h2 className="font-bold text-sm text-slate-100 tracking-tight">Knowledge & Policy</h2>
              <p className="text-[11px] text-slate-400">Live matched runbooks & macros</p>
            </div>
          </div>

          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('articles')}
              className={`px-2 py-1 rounded-md font-medium transition-all ${
                activeTab === 'articles'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Runbooks
            </button>
            <button
              onClick={() => setActiveTab('macros')}
              className={`px-2 py-1 rounded-md font-medium transition-all ${
                activeTab === 'macros'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Macros
            </button>
            <button
              onClick={() => setActiveTab('account')}
              className={`px-2 py-1 rounded-md font-medium transition-all ${
                activeTab === 'account'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              CRM
            </button>
          </div>
        </div>

        {/* Quick Search */}
        <div className="mt-2.5 relative">
          <Search className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search articles, policies, macros..."
            className="w-full bg-slate-950/70 border border-slate-800 focus:border-brand-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none"
          />
        </div>
      </div>

      {/* 2. Main Content Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {activeTab === 'articles' ? (
          /* ARTICLES LIST */
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span className="font-semibold text-slate-300">Context-Ranked Runbooks</span>
              <span className="text-[10px] text-emerald-400 font-mono">Auto-Updating</span>
            </div>

            {filteredArticles.map((article) => {
              const isExpanded = expandedArticleId === article.id;
              return (
                <div
                  key={article.id}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl overflow-hidden shadow-sm transition-all"
                >
                  {/* Article Card Header */}
                  <div
                    onClick={() => setExpandedArticleId(isExpanded ? null : article.id)}
                    className="p-3 cursor-pointer flex items-start justify-between gap-2 hover:bg-slate-800/40 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-slate-200">{article.title}</span>
                      </div>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                          {article.category}
                        </span>
                        <span className="text-[10px] text-slate-500">{article.lastUpdated}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <span className="font-mono text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        {article.relevance}%
                      </span>
                      {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded Body */}
                  {isExpanded && (
                    <div className="p-3 pt-0 border-t border-slate-800/60 bg-slate-950/40 text-xs text-slate-300 space-y-3">
                      <p className="mt-2 text-slate-300 leading-relaxed text-xs">
                        {article.snippet}
                      </p>

                      {/* Action Steps */}
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center space-x-1">
                          <CheckCircle className="h-3.5 w-3.5 text-brand-400" />
                          <span>Standard Operating Steps</span>
                        </div>
                        <ul className="space-y-1 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 text-[11px]">
                          {article.actionSteps.map((step, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="text-brand-400 font-mono font-bold">{idx + 1}.</span>
                              <span className="text-slate-300">{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Policy Exceptions */}
                      {article.policyExceptions.length > 0 && (
                        <div>
                          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 mb-1.5 flex items-center space-x-1">
                            <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
                            <span>Authorized Policy Overrides</span>
                          </div>
                          <ul className="space-y-1 bg-amber-500/5 p-2 rounded-lg border border-amber-500/20 text-[11px] text-amber-200/90">
                            {article.policyExceptions.map((exp, idx) => (
                              <li key={idx} className="flex items-start space-x-1.5">
                                <span className="text-amber-400 font-bold">•</span>
                                <span>{exp}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="pt-2 flex justify-end">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onInsertText(article.snippet);
                          }}
                          className="px-2.5 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-brand-300 rounded-md transition-colors flex items-center space-x-1 border border-slate-700"
                        >
                          <Plus className="h-3 w-3" />
                          <span>Insert Snippet into Draft</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : activeTab === 'macros' ? (
          /* CANNED MACROS */
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span className="font-semibold text-slate-300">Canned Macros</span>
              <span className="text-[10px] text-slate-500">1-Click Insert</span>
            </div>

            {filteredMacros.map((macro) => (
              <div
                key={macro.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-xl shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">{macro.title}</span>
                  <span className="text-[10px] font-mono bg-slate-800 text-brand-400 px-2 py-0.5 rounded border border-slate-700">
                    {macro.shortcut}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-slate-400 line-clamp-2">
                  {macro.text}
                </p>
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">{macro.category}</span>
                  <button
                    onClick={() => onInsertText(macro.text.replace('{customer_name}', customerProfile.name))}
                    className="px-2.5 py-1 text-xs bg-brand-600/20 hover:bg-brand-600 text-brand-300 hover:text-white rounded-md transition-colors font-medium flex items-center space-x-1"
                  >
                    <Plus className="h-3 w-3" />
                    <span>Insert</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* CUSTOMER CRM PROFILE & NOTES */
          <div className="space-y-3 text-xs">
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl space-y-2.5">
              <div className="font-bold text-slate-200 text-xs">Customer Account Overview</div>
              <div className="space-y-1.5 text-slate-300">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Account ID:</span>
                  <span className="font-mono text-slate-200">{customerProfile.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Tier:</span>
                  <span className="font-semibold text-amber-400">{customerProfile.tier}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Lifetime Value:</span>
                  <span className="font-mono font-bold text-brand-400">{customerProfile.clv}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Contract Tenure:</span>
                  <span className="text-slate-200">{customerProfile.tenure}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Historic CSAT:</span>
                  <span className="font-mono text-emerald-400">{customerProfile.csatAverage} / 5.0</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Open Tickets:</span>
                  <span className="font-mono text-red-400 font-bold">{customerProfile.openTickets}</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl space-y-2">
              <div className="font-bold text-slate-200 text-xs flex items-center space-x-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>Frontline Authority Budget</span>
              </div>
              <p className="text-[11px] text-slate-400">
                For {customerProfile.tier} accounts, you are authorized to grant immediate courtesy concessions up to <strong className="text-emerald-400">$150.00</strong> without tier 2 escalation.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

