"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Star, Quote } from "lucide-react";

const testimonials = [
  {
    name: "Sophie Martin",
    role: "Passionnée de généalogie",
    avatar: "SM",
    content:
      "J'ai retrouvé une photo de mes arrière-grands-parents complètement abîmée. Flashback Restore l'a restaurée comme par magie. Voir ma grand-mère pleurer en redécouvrant ce souvenir est un moment que je n'oublierai jamais.",
    rating: 5,
  },
  {
    name: "Thomas Dubois",
    role: "Photographe amateur",
    avatar: "TD",
    content:
      "L'animation des photos est bluffante. J'ai animé une photo de mon père enfant, et le résultat est tellement réaliste que toute la famille était émue. Une technologie vraiment incroyable.",
    rating: 5,
  },
  {
    name: "Marie Lefèvre",
    role: "Maman de 3 enfants",
    avatar: "ML",
    content:
      "J'utilise Flashback Restore pour restaurer les vieilles photos de famille avant de les offrir en cadeau. La qualité est exceptionnelle, et l'application est tellement simple à utiliser. Je la recommande à tout le monde.",
    rating: 5,
  },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: rating }, (_, i) => (
        <Star
          key={i}
          className="w-4 h-4 fill-amber-400 text-amber-400"
        />
      ))}
    </div>
  );
}

function TestimonialCard({
  testimonial,
  index,
}: {
  testimonial: (typeof testimonials)[0];
  index: number;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.15 }}
      className="bg-gray-900 border border-white/5 rounded-2xl p-8 hover:border-white/10 transition-all duration-300 flex flex-col"
    >
      <Quote className="w-8 h-8 text-amber-400/30 mb-4" />
      <p className="text-gray-300 leading-relaxed flex-1 mb-6">
        &ldquo;{testimonial.content}&rdquo;
      </p>
      <div className="flex items-center gap-4 mt-auto pt-6 border-t border-white/5">
        <div className="w-11 h-11 rounded-full bg-gradient-to-br from-amber-400 to-violet-600 flex items-center justify-center text-white font-bold text-sm">
          {testimonial.avatar}
        </div>
        <div>
          <div className="text-white font-medium text-sm">
            {testimonial.name}
          </div>
          <div className="text-gray-500 text-xs">{testimonial.role}</div>
          <div className="mt-1">
            <StarRating rating={testimonial.rating} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default function Testimonials() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="testimonials" className="relative py-24 lg:py-32 bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-amber-400 text-sm font-semibold tracking-widest uppercase">
            Témoignages
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mt-4 mb-6">
            Ce que nos utilisateurs
            <br />
            <span className="text-gradient">disent de nous</span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            Des milliers de personnes ont déjà redonné vie à leurs souvenirs
            avec Flashback Restore.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <TestimonialCard
              key={testimonial.name}
              testimonial={testimonial}
              index={index}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
