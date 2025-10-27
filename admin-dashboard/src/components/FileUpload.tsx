import { useState, useRef } from 'react';
import { uploadApi } from '../lib/api';
import toast from 'react-hot-toast';

interface FileUploadProps {
  type: 'image' | 'audio';
  folder?: string;
  onUploadComplete: (url: string) => void;
  label?: string;
  accept?: string;
  className?: string;
  iconOnly?: boolean;
}

export default function FileUpload({
  type,
  folder,
  onUploadComplete,
  label,
  accept,
  className,
  iconOnly = false
}: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);

    try {
      const result = type === 'image'
        ? await uploadApi.uploadImage(file, folder)
        : await uploadApi.uploadAudio(file, folder);

      onUploadComplete(result.url);
      toast.success(`${type === 'image' ? 'Image' : 'Audio'} uploaded successfully!`);

      // Reset the input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.error || `Failed to upload ${type}`);
    } finally {
      setUploading(false);
    }
  };

  const defaultAccept = type === 'image'
    ? 'image/png,image/jpeg,image/jpg,image/gif,image/webp'
    : 'audio/mpeg,audio/wav,audio/mp4,audio/aac,audio/ogg';

  return (
    <div className={className}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept || defaultAccept}
        onChange={handleFileSelect}
        disabled={uploading}
        className="hidden"
        id={`file-upload-${type}-${folder || 'default'}`}
      />
      <label
        htmlFor={`file-upload-${type}-${folder || 'default'}`}
        title={label || `Upload ${type === 'image' ? 'Image' : 'Audio'}`}
        className={
          iconOnly
            ? `inline-flex items-center justify-center w-10 h-10 rounded-lg cursor-pointer transition-all ${
                uploading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-[#8B6F47]'
              }`
            : `inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-all ${
                uploading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-[#8B6F47] hover:bg-[#6F5838] text-white'
              }`
        }
      >
        {uploading ? (
          <>
            <div className={`inline-block animate-spin rounded-full border-b-2 ${iconOnly ? 'h-5 w-5 border-gray-400' : 'h-4 w-4 border-white'}`}></div>
            {!iconOnly && 'Uploading...'}
          </>
        ) : (
          <>
            <svg className={iconOnly ? 'w-5 h-5' : 'w-4 h-4'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            {!iconOnly && (label || `Upload ${type === 'image' ? 'Image' : 'Audio'}`)}
          </>
        )}
      </label>
    </div>
  );
}
