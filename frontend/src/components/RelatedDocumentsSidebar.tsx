import React from 'react';
import { useNavigate } from 'react-router-dom';
import { usePDF } from '../context/PDFContext';
import { FileText, ExternalLink } from 'lucide-react';

const RelatedDocumentsSidebar: React.FC = () => {
    const { crossDocumentSections } = usePDF();
    const navigate = useNavigate();

    const handleNavigate = (docId: string, page: number) => {
        navigate(`/reader/${docId}?page=${page}`);
    };

    if (crossDocumentSections.length === 0) {
        return null;
    }

    return (
        <div className="w-80 bg-white border-l border-gray-200 h-full overflow-y-auto flex flex-col shadow-sm z-10">
            <div className="p-4 border-b border-gray-100 bg-gray-50/50 backdrop-blur-sm sticky top-0">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-indigo-600" />
                    Related Documents
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                    Found {crossDocumentSections.length} relevant sections in other files
                </p>
            </div>

            <div className="flex-1 p-3 space-y-3">
                {crossDocumentSections.map((section) => (
                    <div
                        key={`${section.documentId}-${section.page}-${section.id}`}
                        className="group p-3 rounded-xl border border-gray-100 bg-white hover:border-indigo-200 hover:shadow-md transition-all duration-200 cursor-pointer relative overflow-hidden"
                        onClick={() => handleNavigate(section.documentId, section.page)}
                    >
                        <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ExternalLink className="w-3 h-3 text-indigo-400" />
                        </div>

                        <div className="flex items-start gap-3 mb-2">
                            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 transition-colors">
                                <FileText className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-medium text-gray-900 truncate" title={section.documentName}>
                                    {section.documentName}
                                </h4>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                                        Page {section.page}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                        {Math.round(section.relevance * 100)}% match
                                    </span>
                                </div>
                            </div>
                        </div>

                        <p className="text-xs text-gray-600 line-clamp-3 leading-relaxed pl-1 border-l-2 border-gray-100 group-hover:border-indigo-200 transition-colors">
                            "{section.snippet}"
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RelatedDocumentsSidebar;
