import { useState } from 'react';
import { Search, Filter, FileText, Calendar, User, Tag, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

interface SearchResult {
  id: string;
  documentId: string;
  documentName: string;
  content: string;
  score: number;
  metadata: {
    author?: string;
    date?: string;
    department?: string;
    tags?: string[];
  };
}

// Mock search results
const mockResults: SearchResult[] = [
  {
    id: '1',
    documentId: 'doc-1',
    documentName: 'Q4 Financial Report 2024.pdf',
    content: 'Revenue increased by 15% compared to Q3, driven by strong performance in the enterprise segment. Operating margins improved to 28%, reflecting cost optimization initiatives...',
    score: 0.95,
    metadata: {
      author: 'Finance Team',
      date: '2024-01-15',
      department: 'Finance',
      tags: ['financial', 'quarterly', 'revenue'],
    },
  },
  {
    id: '2',
    documentId: 'doc-2',
    documentName: 'Employee Handbook.docx',
    content: 'All employees are entitled to 20 days of paid vacation per year. Vacation requests should be submitted at least two weeks in advance through the HR portal...',
    score: 0.87,
    metadata: {
      author: 'HR Department',
      date: '2024-01-01',
      department: 'Human Resources',
      tags: ['policy', 'vacation', 'benefits'],
    },
  },
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchType, setSearchType] = useState<'hybrid' | 'vector' | 'keyword'>('hybrid');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    department: '',
    dateFrom: '',
    dateTo: '',
    fileType: '',
  });

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);

    // Simulate search - in production this calls the API
    setTimeout(() => {
      setResults(mockResults);
      setIsSearching(false);
    }, 500);
  };

  const highlightMatch = (text: string, query: string) => {
    if (!query.trim()) return text;

    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900 mb-4">Document Search</h1>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search across all documents..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching || !query.trim()}
                className={clsx(
                  'px-6 py-3 rounded-lg font-medium transition-colors',
                  query.trim() && !isSearching
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                )}
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </div>

            {/* Search Options */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Search type:</span>
                <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                  {(['hybrid', 'vector', 'keyword'] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setSearchType(type)}
                      className={clsx(
                        'px-3 py-1.5 text-sm capitalize transition-colors',
                        searchType === type
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      )}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
              >
                <Filter className="w-4 h-4" />
                Filters
                <ChevronDown
                  className={clsx('w-4 h-4 transition-transform', showFilters && 'rotate-180')}
                />
              </button>
            </div>

            {/* Filters Panel */}
            {showFilters && (
              <div className="grid grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Department
                  </label>
                  <select
                    value={filters.department}
                    onChange={(e) => setFilters({ ...filters, department: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All</option>
                    <option value="finance">Finance</option>
                    <option value="hr">Human Resources</option>
                    <option value="engineering">Engineering</option>
                    <option value="sales">Sales</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    From Date
                  </label>
                  <input
                    type="date"
                    value={filters.dateFrom}
                    onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    To Date
                  </label>
                  <input
                    type="date"
                    value={filters.dateTo}
                    onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    File Type
                  </label>
                  <select
                    value={filters.fileType}
                    onChange={(e) => setFilters({ ...filters, fileType: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All</option>
                    <option value="pdf">PDF</option>
                    <option value="docx">Word</option>
                    <option value="xlsx">Excel</option>
                    <option value="pptx">PowerPoint</option>
                  </select>
                </div>
              </div>
            )}
          </form>
        </div>
      </header>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-6">
        {results.length > 0 ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Found {results.length} results for "{query}"
            </p>

            {results.map((result) => (
              <div
                key={result.id}
                className="bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <h3 className="font-medium text-blue-600 hover:underline cursor-pointer">
                      {result.documentName}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-400">Score:</span>
                    <span className="text-sm font-medium text-green-600">
                      {(result.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <p className="text-gray-700 text-sm leading-relaxed mb-3">
                  {highlightMatch(result.content, query)}
                </p>

                <div className="flex items-center gap-4 text-xs text-gray-500">
                  {result.metadata.author && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {result.metadata.author}
                    </span>
                  )}
                  {result.metadata.date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {result.metadata.date}
                    </span>
                  )}
                  {result.metadata.tags && result.metadata.tags.length > 0 && (
                    <span className="flex items-center gap-1">
                      <Tag className="w-3 h-3" />
                      {result.metadata.tags.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : query && !isSearching ? (
          <div className="text-center py-12">
            <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No results found for "{query}"</p>
            <p className="text-sm text-gray-400 mt-1">Try different keywords or adjust filters</p>
          </div>
        ) : (
          <div className="text-center py-12">
            <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Search across your enterprise documents</p>
            <p className="text-sm text-gray-400 mt-1">
              Use hybrid search for best results (vector + keyword)
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
