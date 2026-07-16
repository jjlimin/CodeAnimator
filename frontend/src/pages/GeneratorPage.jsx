import React, { useState } from 'react';
import { generateVideo } from '../api/videoApi';
import { useVideoPoll } from '../hooks/useVideoPoll';
import { Search } from 'lucide-react';
import ProcessingState from '../components/Preview/ProcessingState';
import DoneState from '../components/Preview/DoneState';
import CodeInputState from '../components/Preview/CodeInputState';

const GeneratorPage = () => {
  const [code, setCode] = useState('# Paste your code here\nprint("Hello World!")');
  const [jobId, setJobId] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const { status, videoUrl, setStatus } = useVideoPoll(jobId, isGenerating);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      // ה-job_id נוצר בשרת (createJobLambda) ומוחזר בתשובה
      const data = await generateVideo(code);
      setJobId(data.job_id);
    } catch (err) {
      console.error("Failed to start job:", err);
      setIsGenerating(false);
      setStatus('error');
    }
  };

  const handleCancel = () => {
    setIsGenerating(false);
    setJobId(null);
    setStatus('idle');
  };

  return (
    <div className="flex flex-col h-full w-full">

      {/* --- ה-Header שחזר למקומו --- */}
      <header className="flex items-center justify-between mb-8 w-full">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" alt="Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold tracking-tight text-white font-sans">CodeAnimator</span>
        </div>
        <button className="text-gray-400 hover:text-white transition p-2">
          <Search size={20} />
        </button>
      </header>

      {/* --- האזור המרכזי הממורכז --- */}
      <div className="flex-1 flex flex-col items-center justify-center w-full">
        <div className="w-full max-w-4xl">

          {/* מצב 1: הזנת קוד */}
          {(status === 'idle' || status === 'error') && (
            <CodeInputState
              code={code}
              setCode={setCode}
              error={status === 'error'}
              onGenerate={handleGenerate}
            />
          )}

          {/* מצב 2: טעינה ופולינג */}
          {status === 'processing' && (
            <ProcessingState onCancel={handleCancel} />
          )}

          {/* מצב 3: הצגת הוידאו המוכן */}
          {status === 'Done' && (
            <DoneState
              videoUrl={videoUrl}
              code={code}
              onEdit={() => { setIsGenerating(false); setJobId(null); setStatus('idle'); }}
            />
          )}

        </div>
      </div>
    </div>
  );
};

export default GeneratorPage;
