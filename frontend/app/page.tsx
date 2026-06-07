// app/page.tsx
'use client';

import React from 'react';

const motion = {
  div: ({ initial, animate, whileInView, transition, ...props }: any) => React.createElement('div', props),
};

export default function CyberBastionLanding() {
  const features = [
    { title: "Live Response", desc: "Instant remote shell access and automated containment across all endpoints." },
    { title: "Advanced Threat Hunting", desc: "Proactive hunting with MITRE ATT&CK framework and IOC intelligence." },
    { title: "Multi-Tenant SOC", desc: "Unified visibility and management for MSPs and large enterprises." },
  ];

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 bg-black/90 backdrop-blur-md z-50 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-red-600 rounded-lg flex items-center justify-center font-bold text-xl">CB</div>
            <span className="text-2xl font-bold tracking-tighter">CYBERBASTION</span>
          </div>

          <div className="hidden md:flex gap-8 text-sm font-medium">
            {['Features', 'Solutions', 'About'].map((item, i) => (
              <a key={i} href={`#${item.toLowerCase()}`} className="hover:text-red-500 transition-colors">
                {item}
              </a>
            ))}
          </div>

          <button 
            onClick={() => window.location.href = '/dashboard'}
            className="bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-semibold transition"
          >
            Launch SOC Console
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-24 px-6 bg-gradient-to-b from-black to-zinc-950">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 bg-zinc-900 border border-red-900/50 rounded-full px-4 py-1.5 mb-6"
          >
            <span className="text-red-500 animate-pulse">●</span>
            <span className="text-sm font-medium">Real-time Cyber Defense Platform</span>
          </motion.div>

          <h1 className="text-6xl md:text-7xl font-bold tracking-tighter mb-6 leading-tight">
            THE LAST LINE<br />
            <span className="bg-gradient-to-r from-red-500 via-orange-500 to-yellow-500 bg-clip-text text-transparent">
              OF DEFENSE
            </span>
          </h1>

          <p className="text-2xl text-gray-400 mb-10 max-w-3xl mx-auto">
            Enterprise SOC Platform for Threat Detection, Rapid Response &amp; Intelligence
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => alert("Thank you! Our team will contact you soon for a demo.")}
              className="bg-red-600 hover:bg-red-700 text-white text-lg px-10 py-4 rounded-xl font-semibold transition"
            >
              Request Live Demo
            </button>
            <button className="border border-gray-400 hover:bg-white/10 text-lg px-10 py-4 rounded-xl font-semibold transition">
              Watch 2-Min Video
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-zinc-950">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-4xl font-bold text-center mb-16">Built for Modern Security Teams</h2>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="bg-zinc-900 p-8 rounded-2xl border border-gray-800 hover:border-red-600/50 transition-all"
              >
                <div className="w-14 h-14 bg-red-600/10 rounded-2xl mb-6"></div>
                <h3 className="text-2xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-gray-400">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-black py-12 text-center text-gray-500 border-t border-gray-800">
        © 2025 CyberBastion • Enterprise Security Operations Platform
      </footer>
    </div>
  );
}