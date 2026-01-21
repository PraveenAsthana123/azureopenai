import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  FileText,
  Upload,
  Search,
  Filter,
  MoreVertical,
  Download,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';

interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  status: 'processing' | 'indexed' | 'failed';
  uploadedAt: Date;
  chunksCount?: number;
}

// Mock data
const mockDocuments: Document[] = [
  {
    id: '1',
    name: 'Q4 Financial Report 2024.pdf',
    type: 'pdf',
    size: 2456789,
    status: 'indexed',
    uploadedAt: new Date('2024-01-15'),
    chunksCount: 45,
  },
  {
    id: '2',
    name: 'Employee Handbook.docx',
    type: 'docx',
    size: 1234567,
    status: 'indexed',
    uploadedAt: new Date('2024-01-10'),
    chunksCount: 120,
  },
  {
    id: '3',
    name: 'Product Roadmap 2024.pptx',
    type: 'pptx',
    size: 5678901,
    status: 'processing',
    uploadedAt: new Date('2024-01-20'),
  },
];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>(mockDocuments);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'indexed' | 'processing' | 'failed'>('all');
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);

    for (const file of acceptedFiles) {
      const newDoc: Document = {
        id: Date.now().toString(),
        name: file.name,
        type: file.name.split('.').pop() || 'unknown',
        size: file.size,
        status: 'processing',
        uploadedAt: new Date(),
      };

      setDocuments((prev) => [newDoc, ...prev]);

      // Simulate upload and processing
      // In production, this would call the API
      setTimeout(() => {
        setDocuments((prev) =>
          prev.map((doc) =>
            doc.id === newDoc.id
              ? { ...doc, status: 'indexed', chunksCount: Math.floor(Math.random() * 100) + 10 }
              : doc
          )
        );
      }, 3000);
    }

    setUploading(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
  });

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || doc.status === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'indexed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getFileIcon = (type: string) => {
    return <FileText className="w-8 h-8 text-gray-400" />;
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <h1 className="text-xl font-semibold text-gray-900">Documents</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            {documents.filter((d) => d.status === 'indexed').length} indexed documents
          </span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors mb-6',
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 bg-white'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <Upload className="w-6 h-6 text-blue-600" />
            </div>
            <p className="text-gray-700 font-medium mb-1">
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-sm text-gray-500">
              or click to browse (PDF, DOCX, XLSX, PPTX, TXT, MD)
            </p>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value as typeof selectedFilter)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="indexed">Indexed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Documents Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocuments.map((doc) => (
            <div key={doc.id} className="document-card">
              <div className="flex items-start justify-between mb-3">
                {getFileIcon(doc.type)}
                <button className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
                  <MoreVertical className="w-4 h-4 text-gray-400" />
                </button>
              </div>

              <h3 className="font-medium text-gray-900 truncate mb-1" title={doc.name}>
                {doc.name}
              </h3>

              <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
                <span className="uppercase">{doc.type}</span>
                <span>•</span>
                <span>{formatFileSize(doc.size)}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {getStatusIcon(doc.status)}
                  <span
                    className={clsx(
                      'text-sm capitalize',
                      doc.status === 'indexed' && 'text-green-600',
                      doc.status === 'processing' && 'text-blue-600',
                      doc.status === 'failed' && 'text-red-600'
                    )}
                  >
                    {doc.status}
                  </span>
                  {doc.chunksCount && (
                    <span className="text-sm text-gray-400">({doc.chunksCount} chunks)</span>
                  )}
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="w-3 h-3" />
                  {format(doc.uploadedAt, 'MMM d, yyyy')}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2">
                <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                  <Eye className="w-4 h-4" />
                  View
                </button>
                <button className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                  <Download className="w-4 h-4" />
                  Download
                </button>
                <button className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {filteredDocuments.length === 0 && (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No documents found</p>
          </div>
        )}
      </div>
    </div>
  );
}
