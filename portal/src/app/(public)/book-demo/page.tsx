import type { Metadata } from 'next';
import BookDemoForm from './BookDemoForm';

export const metadata: Metadata = {
  title: 'Book a Demo | Corgi',
  description:
    'Schedule a 30-minute demo with a Corgi Account Executive. Pick a time that works for you and we will match you with an AE.',
};

export default function BookDemoPage() {
  return (
    <div className="max-w-[560px] mx-auto px-4 sm:px-6 py-10 md:py-16 flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Book a Demo
        </span>
        <h1 className="font-heading text-[32px] sm:text-[44px] font-medium text-heading tracking-[-1.5px] leading-[1.05]">
          Meet with an Account Executive
        </h1>
        <p className="text-base text-body leading-[1.5]">
          Tell us when you&rsquo;re free and we&rsquo;ll match you with an AE.
          Demos run about 30 minutes.
        </p>
      </header>

      <BookDemoForm />
    </div>
  );
}
