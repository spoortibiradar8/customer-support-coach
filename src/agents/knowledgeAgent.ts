import { KnowledgeArticle, CannedMacro, Message } from '../types';
import { KNOWLEDGE_BASE_ARTICLES, CANNED_MACROS } from '../data/knowledgeBaseData';

export class KnowledgeAgent {
  /**
   * Retrieves and ranks the most relevant knowledge articles based on conversation context.
   */
  public recommendArticles(messages: Message[]): KnowledgeArticle[] {
    if (messages.length === 0) {
      return KNOWLEDGE_BASE_ARTICLES.slice(0, 3);
    }

    const fullConversationText = messages.map(m => m.text).join(' ').toLowerCase();

    return KNOWLEDGE_BASE_ARTICLES.map(article => {
      let score = 40; // baseline

      const articleCorpus = `${article.title} ${article.summary} ${article.snippet} ${article.actionSteps.join(' ')}`.toLowerCase();

      // Check keywords match
      const searchTerms = ['refund', 'double', 'charge', 'amex', 'cancel', 'outage', 'sla', 'webhook', 'sensor', 'damaged', 'hardware', 'mfa', 'password'];
      
      searchTerms.forEach(term => {
        if (fullConversationText.includes(term) && articleCorpus.includes(term)) {
          score += 15;
        }
      });

      // Special contextual overrides
      if (fullConversationText.includes('billed') && article.category === 'Billing') score += 25;
      if (fullConversationText.includes('webhook') && article.category === 'Technical') score += 30;
      if (fullConversationText.includes('sensor') && article.category === 'Hardware') score += 30;
      if (fullConversationText.includes('cancel') && article.category === 'Policy') score += 20;

      return {
        ...article,
        relevance: Math.min(99, Math.max(35, score))
      };
    }).sort((a, b) => b.relevance - a.relevance);
  }

  /**
   * Returns relevant macros based on customer issues.
   */
  public recommendMacros(messages: Message[]): CannedMacro[] {
    if (messages.length === 0) return CANNED_MACROS;
    const text = messages.map(m => m.text).join(' ').toLowerCase();

    if (text.includes('charge') || text.includes('billed') || text.includes('refund')) {
      return [
        CANNED_MACROS.find(m => m.id === 'macro-duplicate-refund')!,
        CANNED_MACROS.find(m => m.id === 'macro-empathy-apology')!,
        CANNED_MACROS.find(m => m.id === 'macro-supervisor-warm-transfer')!,
        CANNED_MACROS.find(m => m.id === 'macro-resolution-wrapup')!
      ].filter(Boolean);
    }

    if (text.includes('down') || text.includes('outage') || text.includes('webhook')) {
      return [
        CANNED_MACROS.find(m => m.id === 'macro-investigating')!,
        CANNED_MACROS.find(m => m.id === 'macro-supervisor-warm-transfer')!,
        CANNED_MACROS.find(m => m.id === 'macro-empathy-apology')!,
        CANNED_MACROS.find(m => m.id === 'macro-resolution-wrapup')!
      ].filter(Boolean);
    }

    return CANNED_MACROS;
  }
}

export const knowledgeAgent = new KnowledgeAgent();

